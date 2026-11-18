"""v0.14: trains a small LoRA adapter on the resident's own examples (QLoRA: the base model loaded in 4-bit).

Runs inside the training toolkit (its own Python with PyTorch, made by the hub's Training tab), never inside the
hub itself. The hub reads the lines this prints:
  STAGE <name>              what it's doing
  BASE_DIR <path>           where the base model's files are
  PROGRESS <step> <total> <loss>
  DONE <adapter dir>
  ERROR <message>
"""
import argparse
import json
import math
import os
import random
import sys
import time


def say(*a):
    print(*a, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-repo", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--epochs", type=float, default=1)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--rank", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    import torch
    from huggingface_hub import snapshot_download
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer

    random.seed(a.seed)
    torch.manual_seed(a.seed)
    cuda = torch.cuda.is_available()

    say("STAGE download")
    base_dir = snapshot_download(a.base_repo, cache_dir=a.cache,
                                 allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt", "*.jinja", "tokenizer*"])
    say("BASE_DIR", base_dir)

    say("STAGE load")
    tok = AutoTokenizer.from_pretrained(base_dir)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    if cuda:
        from transformers import BitsAndBytesConfig
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                               bnb_4bit_compute_dtype=dtype)
        model = AutoModelForCausalLM.from_pretrained(base_dir, quantization_config=q, device_map={"": 0},
                                                     torch_dtype=dtype)
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    else:
        model = AutoModelForCausalLM.from_pretrained(base_dir, torch_dtype=torch.float32)
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()
    model.config.use_cache = False
    targets = [n for n in ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")
               if any(n in name for name, _ in model.named_modules())]
    model = get_peft_model(model, LoraConfig(r=a.rank, lora_alpha=a.rank * 2, lora_dropout=0.05, bias="none",
                                             target_modules=targets, task_type="CAUSAL_LM"))
    device = next(p for p in model.parameters() if p.requires_grad).device

    say("STAGE prepare")
    examples = []
    with open(a.data, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            msgs = json.loads(line)["messages"]
            try:
                full = tok.apply_chat_template(msgs, tokenize=False)
                prompt = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True)
            except Exception:
                full = "\n".join(f"{m['role']}: {m['content']}" for m in msgs) + tok.eos_token
                prompt = "\n".join(f"{m['role']}: {m['content']}" for m in msgs[:-1]) + "\nassistant: "
            ids = tok(full, add_special_tokens=False)["input_ids"][:a.max_len]
            n_prompt = min(len(tok(prompt, add_special_tokens=False)["input_ids"]), len(ids))
            labels = [-100] * n_prompt + ids[n_prompt:]
            if any(x != -100 for x in labels):
                examples.append((ids, labels))
    if not examples:
        say("ERROR no usable examples")
        return 2
    total = max(1, math.ceil(len(examples) * a.epochs / a.accum))
    say(f"STAGE train {len(examples)} examples, {total} steps")

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
    warm = max(1, total // 10)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warm) * max(0.05, 0.5 * (1 + math.cos(math.pi * min(1.0, s / total)))))
    model.train()
    step, seen, running = 0, 0, None
    order = []
    while len(order) < len(examples) * a.epochs:
        batch = list(range(len(examples)))
        random.shuffle(batch)
        order += batch
    order = order[:int(len(examples) * a.epochs)]
    t0 = time.time()
    for i, idx in enumerate(order):
        ids, labels = examples[idx]
        x = torch.tensor([ids], device=device)
        y = torch.tensor([labels], device=device)
        loss = model(input_ids=x, labels=y).loss / a.accum
        loss.backward()
        seen += 1
        running = loss.item() * a.accum if running is None else 0.95 * running + 0.05 * loss.item() * a.accum
        if seen % a.accum == 0 or i == len(order) - 1:
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            step += 1
            say(f"PROGRESS {step} {total} {running:.4f} {int(time.time() - t0)}")
    say("STAGE save")
    os.makedirs(a.out, exist_ok=True)
    model.save_pretrained(a.out)
    tok.save_pretrained(a.out)
    say("DONE", a.out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # the hub shows this line in the Training tab
        msg = str(e).replace("\n", " ")[:500]
        if "out of memory" in msg.lower():
            msg = "The graphics card ran out of memory. Try 'gentle' strength or a smaller model. (" + msg[:200] + ")"
        say("ERROR", msg)
        sys.exit(1)

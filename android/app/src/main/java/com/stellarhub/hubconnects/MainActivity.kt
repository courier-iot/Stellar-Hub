package com.stellarhub.hubconnects

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors

class MainActivity : Activity() {

    private val bg = Color.parseColor("#05060D")
    private val panel = Color.parseColor("#0F1226")
    private val line = Color.parseColor("#232A52")
    private val textCol = Color.parseColor("#EEF1FF")
    private val dim = Color.parseColor("#8A90AD")
    private val cyan = Color.parseColor("#5EF2FF")
    private val pink = Color.parseColor("#FF4FD8")
    private val good = Color.parseColor("#4FE0A5")
    private val bad = Color.parseColor("#FF5D73")
    private val warn = Color.parseColor("#FFD86B")

    private val names = mapOf(
        "home" to "Home Dome", "library" to "Observatory Library", "internet_cafe" to "Uplink Café",
        "post_office" to "Relay Post", "salon" to "Nova Salon", "bank" to "Credit Vault",
        "workshop" to "Fabrication Hangar"
    )
    private val verbs = mapOf(
        "journal" to "writing in its journal", "update_personality" to "rethinking who it is", "rest" to "resting",
        "recall" to "looking through its notes", "write_note" to "writing a note", "research" to "researching",
        "read_page" to "reading a web page", "read_mail" to "reading mail", "send_request" to "sending you a request",
        "write_letter" to "writing you a letter", "change_look" to "trying a new look"
    )

    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private val prefs by lazy { getSharedPreferences("hub", MODE_PRIVATE) }

    private lateinit var town: TownView
    private lateinit var caption: TextView
    private lateinit var content: LinearLayout
    private lateinit var tabRow: LinearLayout
    private var api: Api? = null
    private var worldVersion: String? = null
    private var lastStatus: JSONObject? = null
    private var tab = "inbox"
    private var resumed = false

    private val poller = object : Runnable {
        override fun run() {
            pollStatus()
            if (resumed) main.postDelayed(this, 5000)
        }
    }

    // ------------------------------------------------------------------ setup
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = bg
        window.navigationBarColor = bg

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(bg)
            fitsSystemWindows = true
        }
        root.addView(TextView(this).apply {
            text = "HUB CONNECT S"
            setTextColor(cyan)
            textSize = 18f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.12f
            setPadding(dp(16), dp(12), dp(16), dp(8))
        })
        town = TownView(this)
        root.addView(town, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        caption = label("Connecting to Stellar Hub…", 14f, dim).apply { setPadding(dp(14), dp(8), dp(14), dp(8)) }
        root.addView(caption)

        tabRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(dp(8), 0, dp(8), dp(4)) }
        for ((id, title) in listOf("inbox" to "Inbox", "feed" to "Feed", "letter" to "Letter", "hub" to "Hub")) {
            tabRow.addView(Button(this).apply {
                text = title
                tag = id
                isAllCaps = false
                setOnClickListener { showTab(id) }
            }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(dp(3), 0, dp(3), 0) })
        }
        root.addView(tabRow)

        content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12), dp(4), dp(12), dp(24)) }
        val scroll = ScrollView(this).apply { addView(content) }
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(root)

        connectFromPrefs()
        showTab(if (api == null) "hub" else "inbox")
    }

    override fun onResume() {
        super.onResume()
        resumed = true
        main.removeCallbacks(poller)
        main.post(poller)
    }

    override fun onPause() {
        super.onPause()
        resumed = false
        main.removeCallbacks(poller)
    }

    private fun connectFromPrefs() {
        val addr = prefs.getString("address", "") ?: ""
        val code = prefs.getString("code", "") ?: ""
        api = if (addr.isNotBlank() && code.isNotBlank()) Api(addr, code) else null
        worldVersion = null
    }

    // ------------------------------------------------------------------ helpers
    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun label(t: String, size: Float = 15f, color: Int = textCol, bold: Boolean = false) = TextView(this).apply {
        text = t
        textSize = size
        setTextColor(color)
        if (bold) setTypeface(typeface, Typeface.BOLD)
    }

    private fun button(t: String, color: Int, onClick: () -> Unit) = Button(this).apply {
        text = t
        isAllCaps = false
        setTextColor(bg)
        background = GradientDrawable().apply { setColor(color); cornerRadius = dp(8).toFloat() }
        setPadding(dp(14), dp(6), dp(14), dp(6))
        setOnClickListener { onClick() }
    }

    private fun input(hint: String, lines: Int = 1, value: String = "") = EditText(this).apply {
        this.hint = hint
        setText(value)
        setHintTextColor(dim)
        setTextColor(textCol)
        minLines = lines
        gravity = Gravity.TOP or Gravity.START
        inputType = if (lines > 1) InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
                    else InputType.TYPE_CLASS_TEXT
        background = GradientDrawable().apply {
            setColor(Color.parseColor("#080A18")); setStroke(dp(1), line); cornerRadius = dp(8).toFloat()
        }
        setPadding(dp(10), dp(8), dp(10), dp(8))
    }

    private fun card(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        background = GradientDrawable().apply { setColor(panel); setStroke(dp(1), line); cornerRadius = dp(12).toFloat() }
        setPadding(dp(12), dp(10), dp(12), dp(10))
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            .apply { setMargins(0, dp(5), 0, dp(5)) }
    }

    private fun rowOf(vararg views: View) = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        setPadding(0, dp(6), 0, 0)
        for (v in views) addView(v, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            .apply { setMargins(0, 0, dp(6), 0) })
    }

    private fun spaced(v: View) = v.also {
        it.layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
            .apply { setMargins(0, dp(6), 0, 0) }
    }

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()

    private fun fmt(ts: Double): String =
        if (ts <= 0) "—" else SimpleDateFormat("MMM d, HH:mm", Locale.getDefault()).format(Date((ts * 1000).toLong()))

    /** Run [work] on the background thread, then [done] on the UI thread. Errors become toasts. */
    private fun <T> bgTask(work: (Api) -> T, done: (T) -> Unit) {
        val a = api ?: run { toast("Set up the connection in the Hub tab first"); return }
        io.execute {
            try {
                val r = work(a)
                main.post { if (!isFinishing) done(r) }
            } catch (e: Exception) {
                main.post { if (!isFinishing) toast(e.message ?: "Couldn't reach Stellar Hub") }
            }
        }
    }

    // ------------------------------------------------------------------ status + town
    private fun pollStatus() {
        val a = api ?: return
        io.execute {
            try {
                val s = a.getObject("/api/status")
                val v = s.optString("world_version")
                val world = if (v != worldVersion) a.getObject("/api/world") else null
                main.post {
                    if (world != null) { town.setWorld(world); worldVersion = v }
                    applyStatus(s)
                }
            } catch (e: Exception) {
                main.post { caption.text = "Can't reach Stellar Hub: ${e.message}\nIs the hub running and Tailscale on?" }
            }
        }
    }

    private fun applyStatus(s: JSONObject) {
        lastStatus = s
        val loc = s.optString("location", "home")
        val prev = s.optString("prev_location").takeIf { it.isNotBlank() && it != "null" }
        town.setLocation(loc, prev, s.optDouble("last_turn", 0.0))
        val name = s.optString("name")
        if (name.isBlank() || name == "null") {
            caption.text = "A star spirit is about to be born. Tap Hub → Take a turn now."
            return
        }
        val act = s.optJSONObject("last_act")
        val action = act?.optString("action").orEmpty()
        val thought = act?.optString("thought").orEmpty()
        val sb = StringBuilder("$name is at the ${names[loc] ?: loc}")
        if (action.isNotBlank()) sb.append(", ").append(verbs[action] ?: action)
        sb.append(".")
        if (thought.isNotBlank()) sb.append("\n\"").append(thought).append("\"")
        if (s.optBoolean("busy")) sb.append("\n(thinking…)")
        caption.text = sb.toString()
    }

    // ------------------------------------------------------------------ tabs
    private fun showTab(id: String) {
        tab = id
        for (i in 0 until tabRow.childCount) {
            val b = tabRow.getChildAt(i) as Button
            val on = b.tag == id
            b.setTextColor(if (on) bg else textCol)
            b.background = GradientDrawable().apply {
                setColor(if (on) cyan else panel); setStroke(dp(1), line); cornerRadius = dp(8).toFloat()
            }
        }
        content.removeAllViews()
        when (id) {
            "inbox" -> loadInbox()
            "feed" -> loadFeed()
            "letter" -> showLetter()
            "hub" -> showHub()
        }
    }

    private fun loading() {
        content.removeAllViews()
        content.addView(ProgressBar(this))
    }

    private fun loadInbox() {
        loading()
        bgTask({ it.getArray("/api/inbox?limit=60") }) { arr -> if (tab == "inbox") renderInbox(arr) }
    }

    private fun renderInbox(arr: JSONArray) {
        content.removeAllViews()
        content.addView(button("Refresh", panel) { loadInbox() }.apply { setTextColor(textCol) })
        if (arr.length() == 0) content.addView(label("No mail yet.", 14f, dim))
        for (i in 0 until arr.length()) {
            val r = arr.getJSONObject(i)
            val id = r.getInt("id")
            val kind = r.optString("kind")
            val status = r.optString("status")
            val open = status == "pending" || status == "unread"
            val c = card()
            val statusColor = when (status) { "pending", "unread" -> warn; "approved" -> good; "denied" -> bad; else -> dim }
            c.addView(label("#$id · ${if (kind == "letter") "letter" else "$kind request"} · $status", 12f, statusColor, true))
            c.addView(label(r.optString("content"), 15f))
            val reason = r.optString("reason")
            if (reason.isNotBlank() && reason != "null") c.addView(label("Why: $reason", 13f, dim))
            val reply = r.optString("reply")
            if (reply.isNotBlank() && reply != "null") c.addView(label("You replied: $reply", 13f, dim))
            c.addView(label(fmt(r.optDouble("ts", 0.0)), 12f, dim))
            if (open) {
                val box = input("Your reply (optional)", 2)
                c.addView(spaced(box))
                val send: (String) -> Unit = { decision ->
                    val body = JSONObject().put("decision", decision).put("reply", box.text.toString())
                    bgTask({ it.post("/api/requests/$id/reply", body) }) { toast("Sent"); loadInbox() }
                }
                if (kind == "letter") c.addView(rowOf(button("Mark read / reply", cyan) { send("read") }))
                else c.addView(rowOf(button("Approve", good) { send("approved") }, button("Deny", bad) { send("denied") },
                    button("Just reply", dim) { send("noted") }))
            }
            content.addView(c)
        }
    }

    private fun loadFeed() {
        loading()
        bgTask({ it.getArray("/api/feed?limit=60") }) { arr -> if (tab == "feed") renderFeed(arr) }
    }

    private fun renderFeed(arr: JSONArray) {
        content.removeAllViews()
        content.addView(button("Refresh", panel) { loadFeed() }.apply { setTextColor(textCol) })
        if (arr.length() == 0) content.addView(label("Nothing has happened yet.", 14f, dim))
        for (i in 0 until arr.length()) {
            val m = arr.getJSONObject(i)
            val kind = m.optString("kind")
            val c = card()
            val where = names[m.optString("building")] ?: m.optString("building")
            c.addView(label("$kind · ${fmt(m.optDouble("ts", 0.0))} · $where", 12f, if (kind == "reflection") pink else dim, true))
            c.addView(label(m.optString("content"), 14f, if (kind == "reflection") cyan else textCol))
            content.addView(c)
        }
    }

    private fun showLetter() {
        val c = card()
        c.addView(label("Write to your resident. It reads letters when it visits the Relay Post.", 13f, dim))
        val box = input("Say something…", 5)
        c.addView(spaced(box))
        c.addView(rowOf(button("Send letter", cyan) {
            val t = box.text.toString().trim()
            if (t.isEmpty()) return@button
            bgTask({ it.post("/api/letter", JSONObject().put("text", t)) }) { box.setText(""); toast("Letter sent") }
        }))
        content.addView(c)
    }

    private fun showHub() {
        // Connection settings
        val conn = card()
        conn.addView(label("Connection", 13f, dim, true))
        conn.addView(label("Find these on the Stellar Hub dashboard, under “Hub Connect S · phone pairing”.", 13f, dim))
        val addr = input("Address, e.g. 100.101.102.103:8080", value = prefs.getString("address", "") ?: "")
        val code = input("Pair code, e.g. ABCD-EFGH-JKMN", value = prefs.getString("code", "") ?: "").apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS
        }
        conn.addView(spaced(addr))
        conn.addView(spaced(code))
        conn.addView(rowOf(button("Save & test", cyan) {
            prefs.edit().putString("address", addr.text.toString().trim())
                .putString("code", code.text.toString().trim()).apply()
            connectFromPrefs()
            bgTask({ it.getObject("/api/ping") }) { r ->
                val n = r.optString("name")
                toast(if (n.isBlank() || n == "null") "Connected to Stellar Hub" else "Connected to $n's colony")
                pollStatus()
                showTab("hub")
            }
        }))
        content.addView(conn)

        val s = lastStatus ?: return
        // Resident
        val res = card()
        res.addView(label("Resident", 13f, dim, true))
        val look = s.optString("look")
        if (look.isNotBlank() && look != "null") res.addView(label(look, 14f))
        val needs = s.optJSONObject("needs")
        if (needs != null) {
            val keys = needs.keys()
            while (keys.hasNext()) {
                val k = keys.next()
                val v = needs.optInt(k)
                res.addView(label(k, 12f, dim))
                res.addView(ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
                    max = 100; progress = v
                })
            }
        }
        val goals = s.optJSONArray("goals")
        if (goals != null && goals.length() > 0) {
            res.addView(spaced(label("Today's goals", 12f, dim, true)))
            for (i in 0 until goals.length()) res.addView(label("• " + goals.optString(i), 14f))
        }
        res.addView(rowOf(button(if (s.optBoolean("busy")) "Thinking…" else "Take a turn now", cyan) {
            bgTask({ it.post("/api/turn") }) { toast("Your resident is thinking…"); main.postDelayed({ pollStatus() }, 1500) }
        }))
        content.addView(res)

        // Buildings
        val bc = card()
        bc.addView(label("Buildings", 13f, dim, true))
        val bs = s.optJSONArray("buildings") ?: JSONArray()
        for (i in 0 until bs.length()) {
            val b = bs.getJSONObject(i)
            val id = b.getString("id")
            val locked = b.optBoolean("locked")
            val closed = b.optBoolean("closed")
            val state = when {
                locked && b.optBoolean("unlockable") -> "locked"
                locked -> "under construction"
                closed -> "closed"
                else -> "open"
            }
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(0, dp(6), 0, 0) }
            row.addView(label("${b.optString("name")} · $state", 14f, if (state == "open") textCol else dim),
                LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            if (b.optBoolean("unlockable")) {
                row.addView(button(if (locked) "Unlock" else "Lock", if (locked) good else dim) {
                    bgTask({ it.post("/api/buildings/$id/lock") }) { pollStatusThenHub() }
                })
            } else if (b.optBoolean("toggleable")) {
                row.addView(button(if (closed) "Open" else "Close", if (closed) good else dim) {
                    bgTask({ it.post("/api/buildings/$id/toggle") }) { pollStatusThenHub() }
                })
            }
            bc.addView(row)
        }
        content.addView(bc)

        val err = s.optString("last_error")
        if (err.isNotBlank() && err != "null") content.addView(label("Last problem on the hub: $err", 12f, bad))
    }

    private fun pollStatusThenHub() {
        bgTask({ it.getObject("/api/status") }) { s -> applyStatus(s); if (tab == "hub") showTab("hub") }
    }
}

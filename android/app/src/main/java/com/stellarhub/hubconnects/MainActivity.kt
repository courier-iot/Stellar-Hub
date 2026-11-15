package com.stellarhub.hubconnects

import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
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
        "workshop" to "Fabrication Hangar", "greenhouse" to "Hydro Greenhouse", "radio_tower" to "Radio Tower",
        "archive" to "Archive Vault", "spaceport" to "Spaceport"
    )
    private val verbs = mapOf(
        "journal" to "writing in its journal", "update_personality" to "rethinking who it is", "rest" to "resting",
        "recall" to "looking through its notes", "write_note" to "writing a note", "research" to "researching",
        "read_page" to "reading a web page", "read_mail" to "reading mail", "send_request" to "sending you a request",
        "write_letter" to "writing you a letter", "change_look" to "trying a new look",
        "ask_question" to "asking you a question", "check_balance" to "checking its credits", "buy" to "shopping",
        "check_plants" to "checking its plants", "plant" to "planting a seed", "water" to "watering plants",
        "feed" to "feeding plants", "set_light" to "adjusting grow lamps", "remove" to "clearing a pot",
        "list_music" to "browsing music", "play_music" to "playing music", "stop_music" to "turning the music off",
        "broadcast_log" to "broadcasting a colony log", "archive_memories" to "writing its life story",
        "read_chapter" to "rereading its life story", "start_expedition" to "launching an expedition",
        "read_reports" to "reading old reports", "write_program" to "building a program",
        "list_programs" to "checking its programs", "expedition_return" to "just back from an expedition",
        "build" to "starting construction", "move_building" to "moving a building", "set_bedtime" to "changing its bedtime",
        "stargaze" to "stargazing", "plan_colony" to "planning the colony", "sleep" to "sleeping", "expedition" to "exploring"
    )

    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private val prefs by lazy { getSharedPreferences("hub", MODE_PRIVATE) }

    private lateinit var town: TownView
    private lateinit var header: TextView
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
        header = TextView(this).apply {
            text = "HUB CONNECT S"
            setTextColor(cyan)
            textSize = 18f
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            letterSpacing = 0.12f
            setPadding(dp(16), dp(12), dp(16), dp(8))
        }
        root.addView(header)
        town = TownView(this)
        root.addView(town, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        caption = label("Connecting to Stellar Hub…", 14f, dim).apply { setPadding(dp(14), dp(8), dp(14), dp(8)) }
        root.addView(caption)

        tabRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(dp(8), 0, dp(8), dp(4)) }
        for ((id, title) in listOf("inbox" to "Inbox", "chat" to "Chat", "colony" to "Colony", "feed" to "Feed", "hub" to "Hub")) {
            tabRow.addView(Button(this).apply {
                text = title
                tag = id
                isAllCaps = false
                textSize = 13f
                setPadding(0, 0, 0, 0)
                setOnClickListener { showTab(id) }
            }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(dp(2), 0, dp(2), 0) })
        }
        root.addView(tabRow)

        content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12), dp(4), dp(12), dp(24)) }
        val scroll = ScrollView(this).apply { addView(content) }
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(root)

        Notifier.ensureChannels(this)
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf("android.permission.POST_NOTIFICATIONS"), 1)
        }
        connectFromPrefs()
        if (api != null) Notifier.schedule(this)
        showTab(intent?.getStringExtra("tab") ?: if (api == null) "hub" else "inbox")
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        intent.getStringExtra("tab")?.let { showTab(it) }
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
        val away = s.optJSONObject("away")
        town.setAway(away != null)
        val ev = s.optJSONObject("event")
        town.setLife(s.optString("emote").takeIf { it.isNotBlank() && it != "null" },
            if (s.isNull("daylight")) null else s.optDouble("daylight"), ev?.optString("type"))
        val credits = s.optInt("credits", 0)
        header.text = if (s.optString("name").let { it.isBlank() || it == "null" }) "HUB CONNECT S" else "HUB CONNECT S   ◈ $credits"
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
        val sb = StringBuilder()
        if (s.optBoolean("chat")) {
            sb.append("$name is chatting with you.")
        } else if (s.optBoolean("asleep") && away == null) {
            sb.append("$name is asleep in the Home Dome (until ${s.optJSONObject("sleep")?.optInt("wake")}:00).")
        } else if (away != null) {
            sb.append("$name is away on an expedition: ${away.optString("topic")}")
            sb.append(" (back around ${fmt(away.optDouble("return_ts", 0.0))}).")
        } else {
            sb.append("$name is at the ${names[loc] ?: loc}")
            if (action.isNotBlank()) sb.append(", ").append(verbs[action] ?: action)
            sb.append(".")
            if (thought.isNotBlank()) sb.append("\n\"").append(thought).append("\"")
        }
        ev?.let { sb.append("\n").append(it.optString("title")).append(": ").append(it.optString("about").take(140)) }
        s.optJSONObject("now_playing")?.let { np ->
            sb.append("\n♪ ").append(np.optString("title")).append(" by ").append(np.optString("artist"))
        }
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
            "colony" -> loadColony()
            "feed" -> loadFeed()
            "chat" -> loadChat()
            "hub" -> showHub()
        }
    }

    private fun loading() {
        content.removeAllViews()
        content.addView(ProgressBar(this))
    }

    private fun loadInbox() {
        loading()
        bgTask({ Pair(it.getArray("/api/inbox?limit=60"), it.getObject("/api/colony")) }) { (arr, col) ->
            if (tab == "inbox") renderInbox(arr, col)
        }
    }

    private fun renderInbox(arr: JSONArray, col: JSONObject) {
        val programs = HashMap<Int, JSONObject>()
        col.optJSONArray("programs")?.let { ps -> for (i in 0 until ps.length()) ps.getJSONObject(i).let { programs[it.getInt("id")] = it } }
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
            val kindLabel = when (kind) {
                "letter" -> "letter"; "question" -> "question"; "run_program" -> "program to run"; else -> "$kind request"
            }
            c.addView(label("#$id · $kindLabel · $status", 12f, statusColor, true))
            c.addView(label(r.optString("content"), 15f))
            if (kind == "run_program") {
                val pid = JSONObject(r.optString("extra").takeIf { it.isNotBlank() && it != "null" } ?: "{}").optInt("program_id")
                programs[pid]?.let { p ->
                    c.addView(spaced(label(p.optString("code"), 12f, cyan).apply {
                        typeface = Typeface.MONOSPACE
                        background = GradientDrawable().apply { setColor(Color.parseColor("#080A18")); cornerRadius = dp(8).toFloat() }
                        setPadding(dp(8), dp(8), dp(8), dp(8))
                    }))
                }
            }
            val reason = r.optString("reason")
            if (reason.isNotBlank() && reason != "null") c.addView(label("Why: $reason", 13f, dim))
            val reply = r.optString("reply")
            if (reply.isNotBlank() && reply != "null") c.addView(label("You replied: $reply", 13f, dim))
            c.addView(label(fmt(r.optDouble("ts", 0.0)), 12f, dim))
            if (open) {
                val box = input(if (kind == "question") "Your answer" else "Your reply (optional)", 2)
                c.addView(spaced(box))
                val send: (String) -> Unit = { decision ->
                    val body = JSONObject().put("decision", decision).put("reply", box.text.toString())
                    bgTask({ it.post("/api/requests/$id/reply", body) }) { toast("Sent"); loadInbox() }
                }
                when (kind) {
                    "letter" -> c.addView(rowOf(button("Mark read / reply", cyan) { send("read") }))
                    "question" -> c.addView(rowOf(button("Answer", cyan) { send("noted") }))
                    "run_program" -> c.addView(rowOf(button("Run it", good) { send("approved") }, button("Don't run", bad) { send("denied") }))
                    else -> c.addView(rowOf(button("Approve", good) { send("approved") }, button("Deny", bad) { send("denied") },
                        button("Just reply", dim) { send("noted") }))
                }
            }
            content.addView(c)
        }
    }

    private fun loadColony() {
        loading()
        bgTask({ Pair(it.getObject("/api/colony"), it.getArray("/api/milestones")) }) { (col, ms) ->
            if (tab == "colony") { renderColony(col); renderMilestones(ms) }
        }
    }

    private fun renderMilestones(ms: JSONArray) {
        val s = lastStatus
        if (s != null) {
            val plan = section("COLONY PLAN")
            s.optString("map").split("; ").forEach { plan.addView(label(it, 13f, if (it.endsWith("empty")) dim else textCol)) }
            val bp = s.optJSONArray("blueprints")
            if (bp != null && bp.length() > 0) {
                val names = (0 until bp.length()).joinToString(", ") { this.names[bp.optString(it)] ?: bp.optString(it) }
                plan.addView(spaced(label("Blueprints waiting to be built: $names", 13f, warn)))
            }
            s.optJSONObject("sleep")?.let { plan.addView(spaced(label("Sleeps ${it.optInt("bed")}:00 to ${it.optInt("wake")}:00", 13f, dim))) }
        }
        val m = section("MILESTONES")
        if (ms.length() == 0) m.addView(label("No milestones yet.", 13f, dim))
        for (i in 0 until ms.length()) {
            val o = ms.getJSONObject(i)
            val r = o.optInt("reward")
            m.addView(spaced(label("🏆 ${o.optString("title")}", 14f, textCol, true)))
            m.addView(label(fmt(o.optDouble("ts", 0.0)) + if (r > 0) " · +$r credits" else "", 12f, dim))
        }
    }

    private fun section(title: String): LinearLayout = card().also {
        it.addView(label(title, 13f, dim, true))
        content.addView(it)
    }

    private fun renderColony(col: JSONObject) {
        content.removeAllViews()
        content.addView(button("Refresh", panel) { loadColony() }.apply { setTextColor(textCol) })

        // Credit Vault
        val cv = section("CREDIT VAULT")
        cv.addView(label("◈ ${col.optInt("credits")} credits", 20f, warn, true))
        val amt = input("Amount", value = "10").apply { inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_SIGNED }
        val note = input("What for? (e.g. great question)")
        cv.addView(spaced(amt)); cv.addView(spaced(note))
        cv.addView(rowOf(button("Give credits", warn) {
            val n = amt.text.toString().toIntOrNull() ?: 0
            if (n == 0) return@button
            bgTask({ it.post("/api/credits/bonus", JSONObject().put("amount", n).put("note", note.text.toString())) }) {
                toast("Sent"); loadColony()
            }
        }))
        val ledger = col.optJSONArray("ledger") ?: JSONArray()
        for (i in 0 until minOf(8, ledger.length())) {
            val l = ledger.getJSONObject(i)
            val a = l.optInt("amount")
            cv.addView(label("${if (a > 0) "+" else ""}$a  ${l.optString("reason")}", 13f, if (a > 0) good else bad))
        }

        // Greenhouse
        val gh = section("HYDRO GREENHOUSE")
        val plants = col.optJSONArray("plants") ?: JSONArray()
        if (plants.length() == 0) gh.addView(label("No plants yet.", 13f, dim))
        for (i in 0 until plants.length()) {
            val p = plants.getJSONObject(i)
            val alive = p.optInt("alive") == 1
            gh.addView(spaced(label("${p.optString("name")} · ${p.optString("tier")} · ${if (alive) p.optString("stage") else "wilted"}",
                14f, if (alive) textCol else bad, true)))
            gh.addView(ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply { max = 100; progress = p.optInt("health") })
            gh.addView(label(p.optString("line").substringAfter(": "), 12f, dim))
        }

        // Radio Tower
        val rt = section("RADIO TOWER")
        val np = col.optJSONObject("now_playing")
        if (np != null) {
            rt.addView(label("♪ ${np.optString("title")} by ${np.optString("artist")}", 15f, cyan))
            rt.addView(rowOf(button("Stop music", dim) { bgTask({ it.post("/api/radio/stop") }) { loadColony() } }))
        } else rt.addView(label("Nothing playing.", 13f, dim))
        rt.addView(label("${col.optInt("music_count")} songs on the shelf", 12f, dim))
        val logs = col.optJSONArray("broadcasts") ?: JSONArray()
        for (i in 0 until minOf(5, logs.length())) {
            val b = logs.getJSONObject(i)
            rt.addView(spaced(label("📡 ${fmt(b.optDouble("ts", 0.0))}", 12f, dim)))
            rt.addView(label(b.optString("text"), 14f))
        }

        // Spaceport
        val sp = section("SPACEPORT")
        val ex = col.optJSONObject("expedition")
        if (ex != null) {
            val legs = ex.optJSONArray("legs")?.length() ?: 0
            sp.addView(label("🚀 Away: ${ex.optString("topic")} (stop ${ex.optInt("done")}/$legs, back ~${fmt(ex.optDouble("return_ts", 0.0))})", 14f, cyan))
        }
        val reports = col.optJSONArray("reports") ?: JSONArray()
        if (ex == null && reports.length() == 0) sp.addView(label("No expeditions yet.", 13f, dim))
        for (i in 0 until reports.length()) {
            val r = reports.getJSONObject(i)
            sp.addView(spaced(label(r.optString("topic"), 14f, textCol, true)))
            sp.addView(label(r.optString("report"), 13f, dim))
        }

        // Fabrication Hangar
        val fh = section("FABRICATION HANGAR")
        if (!col.optBoolean("sandbox")) fh.addView(label("Sandbox not installed on the hub (sudo apt install bubblewrap).", 12f, warn))
        val progs = col.optJSONArray("programs") ?: JSONArray()
        if (progs.length() == 0) fh.addView(label("No programs yet.", 13f, dim))
        for (i in 0 until progs.length()) {
            val p = progs.getJSONObject(i)
            fh.addView(spaced(label("${p.optString("name")} · ${p.optString("status").replace('_', ' ')}", 14f, textCol, true)))
            fh.addView(label(p.optString("description"), 12f, dim))
            val out = p.optString("output")
            if (out.isNotBlank() && out != "null") fh.addView(label(out, 12f, cyan).apply { typeface = Typeface.MONOSPACE })
        }

        // Archive Vault
        val av = section("ARCHIVE VAULT · LIFE STORY")
        val chapters = col.optJSONArray("chapters") ?: JSONArray()
        if (chapters.length() == 0) av.addView(label("No chapters yet.", 13f, dim))
        for (i in 0 until chapters.length()) {
            val ch = chapters.getJSONObject(i)
            av.addView(spaced(label(ch.optString("title"), 14f, textCol, true)))
            av.addView(label(ch.optString("text"), 13f, dim))
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

    private fun loadChat() {
        loading()
        bgTask({ it.getObject("/api/chat") }) { st -> if (tab == "chat") renderChat(st) }
    }

    private fun renderChat(st: JSONObject) {
        content.removeAllViews()
        val c = card()
        c.addView(label("LIVE CHAT", 13f, dim, true))
        c.addView(label("Your resident pauses what it's doing to talk with you, and remembers the conversation afterwards.", 12f, dim))
        val msgs = st.optJSONArray("messages") ?: JSONArray()
        for (i in 0 until msgs.length()) {
            val m = msgs.getJSONObject(i)
            val mine = m.optString("who") == "creator"
            c.addView(spaced(label(if (mine) "You" else (lastStatus?.optString("name") ?: "Resident"), 12f, if (mine) warn else cyan, true)))
            c.addView(label(m.optString("text"), 15f))
        }
        val box = input("Say something…", 2)
        c.addView(spaced(box))
        val sendBtn = button("Send", cyan) { }
        sendBtn.setOnClickListener {
            val t = box.text.toString().trim()
            if (t.isEmpty()) return@setOnClickListener
            sendBtn.isEnabled = false
            sendBtn.text = "Thinking…"
            bgTask({ it.post("/api/chat/say", JSONObject().put("text", t)) }) { r ->
                if (tab == "chat") r.optJSONObject("chat")?.let { renderChat(it) }
            }
        }
        c.addView(rowOf(sendBtn, button("End chat", dim) {
            bgTask({ it.post("/api/chat/end") }) { toast("Chat saved to its memories"); loadChat() }
        }))
        content.addView(c)

        val lc = card()
        lc.addView(label("WRITE A LETTER", 13f, dim, true))
        lc.addView(label("Letters wait at the Relay Post until your resident visits.", 12f, dim))
        val lbox = input("Dear…", 4)
        lc.addView(spaced(lbox))
        lc.addView(rowOf(button("Send letter", cyan) {
            val t = lbox.text.toString().trim()
            if (t.isEmpty()) return@button
            bgTask({ it.post("/api/letter", JSONObject().put("text", t)) }) { lbox.setText(""); toast("Letter sent") }
        }))
        content.addView(lc)
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
                .putString("code", code.text.toString().trim()).putInt("last_event", -1).apply()
            connectFromPrefs()
            Notifier.schedule(this)
            io.execute { try { Notifier.check(applicationContext) } catch (_: Exception) { } }
            bgTask({ it.getObject("/api/ping") }) { r ->
                val n = r.optString("name")
                toast(if (n.isBlank() || n == "null") "Connected to Stellar Hub" else "Connected to $n's colony")
                pollStatus()
                showTab("hub")
            }
        }))
        content.addView(conn)

        // Notifications
        val nc = card()
        nc.addView(label("Notifications", 13f, dim, true))
        nc.addView(label("Requests, questions, letters and colony news. Checked about every 15 minutes " +
            "(keep Tailscale on). Approve, deny or answer right from the notification.", 13f, dim))
        val on = prefs.getBoolean("notify", true)
        val qs = input("Quiet from (hour 0-23)", value = prefs.getInt("quiet_start", 22).toString()).apply { inputType = InputType.TYPE_CLASS_NUMBER }
        val qe = input("Quiet until (hour 0-23)", value = prefs.getInt("quiet_end", 7).toString()).apply { inputType = InputType.TYPE_CLASS_NUMBER }
        nc.addView(spaced(label("Quiet hours (no notifications):", 13f)))
        nc.addView(spaced(qs)); nc.addView(spaced(qe))
        nc.addView(rowOf(
            button(if (on) "Notifications: ON" else "Notifications: OFF", if (on) good else dim) {
                prefs.edit().putBoolean("notify", !on).apply(); showTab("hub")
            },
            button("Save quiet hours", cyan) {
                val a = qs.text.toString().toIntOrNull()?.coerceIn(0, 23) ?: 22
                val b = qe.text.toString().toIntOrNull()?.coerceIn(0, 23) ?: 7
                prefs.edit().putInt("quiet_start", a).putInt("quiet_end", b).apply()
                toast("Quiet from $a:00 to $b:00")
            }
        ))
        content.addView(nc)

        val s = lastStatus ?: return
        // Resident
        val res = card()
        res.addView(label("Resident", 13f, dim, true))
        res.addView(label("◈ ${s.optInt("credits")} credits", 15f, warn, true))
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
            }
            if (b.optBoolean("toggleable")) {
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

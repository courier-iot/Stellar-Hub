package com.stellarhub.hubconnects

import android.app.Activity
import android.app.SearchManager
import android.content.ContentValues
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.media.MediaPlayer
import android.net.Uri
import android.provider.MediaStore
import android.widget.ImageView
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.graphics.Color
import android.graphics.Typeface
import kotlin.math.roundToInt
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
        "workshop" to "Fabrication Hangar", "pet_shop" to "Pet Shop", "store" to "Department Store", "museum" to "Stellar Museum", "greenhouse" to "Hydro Greenhouse", "radio_tower" to "Radio Tower",
        "archive" to "Archive Vault", "spaceport" to "Spaceport", "gallery" to "Starlight Gallery", "park" to "Low-G Park",
        "studio" to "Radio Studio", "station" to "Orbital Station", "exchange" to "Curio Exchange",
        "mech_shop" to "Mechanical Workshop"
    )
    private val verbs = mapOf(
        "view_challenge" to "reading this week's challenge", "attempt_challenge" to "coding a challenge",
        "view_workshop" to "checking its parts", "design_machine" to "designing a machine", "maintain_machine" to "servicing a machine",
        "design_plan" to "designing a project for you", "buy_accessory" to "buying something to wear", "wear" to "trying on accessories",
        "paint_building" to "repainting a building",
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
        "stargaze" to "stargazing", "plan_colony" to "planning the colony", "sleep" to "sleeping", "expedition" to "exploring",
        "paint" to "painting", "showcase" to "arranging its home", "remove_showcase" to "rearranging its home",
        "upgrade_home" to "adding a floor to its home", "view_collection" to "admiring its collection",
        "observe_sky" to "at the telescope", "write" to "writing", "relax" to "relaxing in the park",
        "solve_puzzle" to "solving a puzzle", "hang_painting" to "hanging a painting", "compose" to "composing music",
        "play_composition" to "playing its own song", "station_study" to "studying",
        "check_exchange" to "browsing the Exchange", "sell_curio" to "selling curios", "trade_up" to "trading up curios",
        "auction_curio" to "starting an auction", "list_phone_music" to "browsing the music on your phone",
        "play_phone_music" to "playing a song on your phone",
        "browse_pets" to "looking at pets", "adopt_pet" to "adopting a pet", "train_pet" to "training a pet",
        "check_pets" to "checking on its pets", "feed_pets" to "feeding its pets", "play_with_pet" to "playing with a pet",
        "rest_pet" to "resting a pet", "treat_pet" to "taking a pet to the clinic", "rescue_pet" to "rescuing a pet",
        "work_pet" to "putting a pet to work", "decorate" to "decorating", "host_show" to "hosting its radio show",
        "make_gift" to "making you a gift", "talk_to_visitor" to "talking with a visitor", "read_manual" to "reading a manual",
        "read_plant_guide" to "reading the plant guide", "browse_store" to "browsing the store",
        "view_museum" to "walking the museum", "donate_set" to "donating a set to the museum",
        "sell_set" to "selling a set to the curator", "build_upper_street" to "building the Upper Street"
    )
    private val hobbyIcons = mapOf("painting" to "🎨", "writing" to "✍️", "composing" to "🎼", "astronomy" to "🔭",
        "collecting" to "🧺", "games" to "♟️", "gardening" to "🌱", "coding" to "🛠")

    private val io = Executors.newSingleThreadExecutor()
    private val side = Executors.newSingleThreadExecutor()   // rooms and the music list, so a long chat reply doesn't hold them up
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
    private var player: MediaPlayer? = null
    private var chessSel: String? = null
    private var lastPalette: Map<Char, Int>? = null
    private lateinit var turnBtn: Button
    private lateinit var viewBtn: Button
    private lateinit var followBtn: Button

    private val poller = object : Runnable {
        override fun run() {
            pollStatus()
            if (resumed) main.postDelayed(this, 5000)
        }
    }

    // ------------------------------------------------------------------ setup
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        installCrashReporter()
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
        val headRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        headRow.addView(header, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        headRow.addView(Button(this).apply {
            text = "📷"
            isAllCaps = false
            background = GradientDrawable().apply { setColor(panel); setStroke(dp(1), line); cornerRadius = dp(8).toFloat() }
            setOnClickListener { savePhoto() }
        }, LinearLayout.LayoutParams(dp(52), dp(40)).apply { setMargins(0, 0, dp(10), 0) })
        root.addView(headRow)
        town = TownView(this)
        town.follow = prefs.getBoolean("follow", true)
        town.onNeedRoom = { id -> fetchRoom(id) }
        town.onViewChanged = { updateViewButtons() }
        root.addView(town, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        // controls right under the colony: take a turn, step inside / outside, follow on or off
        turnBtn = smallButton("▶ Take a turn", cyan) { takeTurn() }
        viewBtn = smallButton("Go inside", textCol) { town.showInside(!town.isInside) }
        followBtn = smallButton("", textCol) {
            town.follow = !town.follow
            prefs.edit().putBoolean("follow", town.follow).apply()
            if (town.follow && town.canGoInside) town.showInside(true)
            updateViewButtons()
        }
        val controls = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(dp(8), dp(6), dp(8), 0) }
        controls.addView(turnBtn, LinearLayout.LayoutParams(0, dp(38), 1.3f).apply { setMargins(dp(2), 0, dp(2), 0) })
        controls.addView(viewBtn, LinearLayout.LayoutParams(0, dp(38), 1f).apply { setMargins(dp(2), 0, dp(2), 0) })
        controls.addView(followBtn, LinearLayout.LayoutParams(0, dp(38), 1f).apply { setMargins(dp(2), 0, dp(2), 0) })
        root.addView(controls)
        updateViewButtons()
        caption = label("Connecting to Stellar Hub…", 14f, dim).apply { setPadding(dp(14), dp(8), dp(14), dp(8)) }
        root.addView(caption)

        tabRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(dp(8), 0, dp(8), dp(4)) }
        for ((id, title) in listOf("inbox" to "Inbox", "chat" to "Chat", "colony" to "Colony", "build" to "Build", "gallery" to "Gallery", "feed" to "Feed", "hub" to "Hub")) {
            tabRow.addView(Button(this).apply {
                text = title
                tag = id
                isAllCaps = false
                textSize = 12f
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
        showCrashReportIfAny()
        connectFromPrefs()
        if (api != null) Notifier.schedule(this)?.let { toast(it) }
        showTab(intent?.getStringExtra("tab") ?: if (api == null) "hub" else "inbox")
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        intent.getStringExtra("tab")?.let { showTab(it) }
    }

    override fun onResume() {
        super.onResume()
        resumed = true
        ListenQueue.appVisible = true
        side.execute { ListenQueue.flush(this, foreground = true) }
        main.removeCallbacks(poller)
        main.post(poller)
        if (::town.isInitialized) town.wave()
        refreshMe()
        if (prefs.getBoolean("share_music", false) && api != null &&
            System.currentTimeMillis() - prefs.getLong("music_synced", 0L) > 24 * 3600 * 1000L &&
            checkSelfPermission(audioPermission) == PackageManager.PERMISSION_GRANTED) shareMusic(false)
    }

    override fun onPause() {
        super.onPause()
        resumed = false
        ListenQueue.appVisible = false
        main.removeCallbacks(poller)
    }

    /** If the app ever crashes, save what happened so it can be shown (and photographed) next time. */
    private fun installCrashReporter() {
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        val store = getSharedPreferences("crash", MODE_PRIVATE)
        Thread.setDefaultUncaughtExceptionHandler { t, e ->
            try {
                val trace = android.util.Log.getStackTraceString(e).take(3000)
                store.edit().putString("report", "Hub Connect S ${appVersion()} · Android ${Build.VERSION.RELEASE}\n" +
                    "Thread: ${t.name}\n$trace").commit()
            } catch (_: Throwable) { }
            previous?.uncaughtException(t, e)
        }
    }

    private fun appVersion(): String = try {
        packageManager.getPackageInfo(packageName, 0).versionName ?: "?"
    } catch (_: Exception) { "?" }

    private fun showCrashReportIfAny() {
        val store = getSharedPreferences("crash", MODE_PRIVATE)
        val report = store.getString("report", null) ?: return
        android.app.AlertDialog.Builder(this)
            .setTitle("The app crashed last time")
            .setMessage("Please send a screenshot of this so it can be fixed:\n\n$report")
            .setPositiveButton("Dismiss") { _, _ -> store.edit().remove("report").apply() }
            .setNeutralButton("Copy") { _, _ ->
                val cb = getSystemService(android.content.ClipboardManager::class.java)
                cb.setPrimaryClip(android.content.ClipData.newPlainText("Hub Connect S crash", report))
                store.edit().remove("report").apply()
                toast("Copied")
            }
            .show()
    }

    private fun connectFromPrefs() {
        val addr = prefs.getString("address", "") ?: ""
        var code = prefs.getString("code", "") ?: ""
        if (Api.looksLikePairCode(code)) {        // from before v0.13.2: that was the shared pair code, now this phone joins
            prefs.edit().putString("pair_code", code).remove("code").apply()
            code = ""
        }
        api = if (addr.isNotBlank() && code.isNotBlank()) Api(addr, code, foreground = true) else null
        worldVersion = null
    }

    private val myRole get() = prefs.getString("role", "owner") ?: "owner"
    private val isOwner get() = myRole == "owner"

    /** Asks the hub who this device is signed in as, and remembers its username and role. */
    private fun refreshMe(done: (() -> Unit)? = null) {
        val a = api ?: return
        io.execute {
            try {
                val me = a.getObject("/api/me")
                main.post {
                    prefs.edit().putString("username", me.optString("name")).putString("role", me.optString("role", "member"))
                        .putString("join_status", me.optString("status")).apply()
                    done?.invoke()
                }
            } catch (e: Exception) { }
        }
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

    private fun smallButton(t: String, color: Int, onClick: () -> Unit) = Button(this).apply {
        text = t
        isAllCaps = false
        textSize = 12f
        setTextColor(color)
        setPadding(dp(4), 0, dp(4), 0)
        background = GradientDrawable().apply { setColor(panel); setStroke(dp(1), line); cornerRadius = dp(8).toFloat() }
        setOnClickListener { onClick() }
    }

    private fun updateViewButtons() {
        if (!::viewBtn.isInitialized) return
        viewBtn.text = if (town.isInside) "◀ Outside" else "Go inside ▶"
        viewBtn.isEnabled = town.isInside || town.canGoInside
        viewBtn.alpha = if (viewBtn.isEnabled) 1f else 0.45f
        followBtn.text = if (town.follow) "Follow: ON" else "Follow: OFF"
        followBtn.setTextColor(if (town.follow) good else dim)
    }

    private fun takeTurn() {
        if (lastStatus?.optBoolean("busy") == true) { toast("It's already thinking…"); return }
        turnBtn.text = "Thinking…"
        bgTask({ it.post("/api/turn") }) {
            toast("Your resident is taking a turn…")
            main.postDelayed({ pollStatus() }, 1500)
        }
    }

    private fun fetchRoom(id: String) {
        val a = api ?: return
        side.execute {
            try {
                val room = a.getObject("/api/interior/$id")
                main.post { if (!isFinishing) town.setRoom(room) }
            } catch (e: Exception) {
                main.post { town.roomFailed(id) }
            }
        }
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
                // a missing page on an older hub isn't a lost connection: say so without taking over the status line
                main.post { if (!isFinishing) { val m = explain(e); toast(m); if (e.message != "NEEDS_NEWER_HUB") caption.text = m } }
            }
        }
    }

    /** Newer than the hub? Compares "0.13.3"-style versions. */
    private fun older(a: String, b: String): Boolean {
        val x = a.split(".").map { it.toIntOrNull() ?: 0 }
        val y = b.split(".").map { it.toIntOrNull() ?: 0 }
        for (i in 0 until maxOf(x.size, y.size)) {
            val p = x.getOrElse(i) { 0 }
            val q = y.getOrElse(i) { 0 }
            if (p != q) return p < q
        }
        return false
    }

    // ------------------------------------------------------------------ status + town
    private fun pollStatus() {
        val a = api ?: run {
            caption.text = "Not connected yet. Open the Hub tab, enter the address and pair code from the dashboard, create your username, then tap Join."
            return
        }
        io.execute {
            try {
                val s = a.getObject("/api/status")
                val v = s.optString("world_version")
                val world = if (v != worldVersion) a.getObject("/api/world") else null
                main.post {
                    if (world != null) {
                        town.setWorld(world); worldVersion = v
                        lastPalette = try { Pixel.palette(world.getJSONObject("palette")) } catch (e: Exception) { lastPalette }
                    }
                    applyStatus(s)
                }
            } catch (e: Exception) {
                main.post { caption.text = explain(e) }
            }
        }
    }

    private fun explain(e: Exception): String = when {
        e.message == "Wrong pair code" -> "Wrong pair code. Check it on the dashboard and join again."
        e.message == "Waiting for approval" -> "Waiting for the owner to approve “${prefs.getString("username", "")}” on the Stellar Hub dashboard…"
        e.message == "Not signed in" -> "This phone isn't signed in (or was removed). Open the Hub tab and join again."
        e.message == "NEEDS_NEWER_HUB" -> "This part needs a newer Stellar Hub. Update the hub on your PC (dashboard → Hub → Check for updates)."
        e is java.net.SocketTimeoutException || e is java.net.ConnectException || e is java.net.NoRouteToHostException ->
            "Can't reach Stellar Hub at ${api?.base}.\nCheck: hub running · Tailscale on (phone and PC) · Windows Firewall rule (run Setup on the PC)."
        e is java.net.UnknownHostException -> "That address doesn't exist. Use the 100.x.x.x address from the dashboard."
        else -> "Can't reach Stellar Hub: ${e.message}"
    }

    private fun applyStatus(s: JSONObject) {
        lastStatus = s
        val loc = s.optString("location", "home")
        val away = s.optJSONObject("away")
        town.setAway(away != null)
        town.setOrbit(s.optBoolean("in_orbit"))
        val ev = s.optJSONObject("event")
        town.setMood(s.optString("mood").takeIf { it.isNotBlank() && it != "null" }, s.optInt("hour", 12), s.optBoolean("asleep"))
        town.setLife(s.optString("emote").takeIf { it.isNotBlank() && it != "null" },
            if (s.isNull("daylight")) null else s.optDouble("daylight"), ev?.optString("type"))
        val credits = s.optInt("credits", 0)
        header.text = if (s.optString("name").let { it.isBlank() || it == "null" }) "HUB CONNECT S" else "HUB CONNECT S   ◈ $credits"
        val prev = s.optString("prev_location").takeIf { it.isNotBlank() && it != "null" }
        val room = s.optJSONObject("interior")
        town.setPlace(loc, prev, s.optDouble("last_turn", 0.0),
            room?.optString("action")?.takeIf { it.isNotBlank() && it != "null" },
            room?.optString("version")?.takeIf { it.isNotBlank() && it != "null" })
        if (::turnBtn.isInitialized) {
            turnBtn.text = if (s.optBoolean("busy")) "Thinking…" else "▶ Take a turn"
            updateViewButtons()
        }
        s.optJSONObject("phone_play")?.let { playOnPhone(it) }
        town.setListening(room?.optJSONObject("listening") != null)
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
        } else if (s.optBoolean("in_orbit")) {
            sb.append("$name is up at the Orbital Station, studying.")
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
        val appV = try { packageManager.getPackageInfo(packageName, 0).versionName ?: "" } catch (e: Exception) { "" }
        val hubV = s.optString("hub_version").takeIf { it.isNotBlank() && it != "null" }
        if (hubV == null || (appV.isNotBlank() && older(hubV, appV)))
            sb.append("\n⚠ Your hub (${hubV?.let { "v$it" } ?: "an older version"}) is behind this app (v$appV). Update Stellar Hub on your PC: dashboard → Hub → Check for updates.")
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
            "build" -> loadWorkshop()
            "gallery" -> loadGallery()
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
        bgTask({ Triple(it.getArray("/api/inbox?limit=60"), it.getObject("/api/colony"), it.getObject("/api/gifts")) }) { (arr, col, gifts) ->
            if (tab == "inbox") { renderInbox(arr, col); renderGifts(gifts) }
        }
    }

    private fun renderGifts(g: JSONObject) {
        val gifts = g.optJSONArray("gifts") ?: return
        if (gifts.length() == 0) return
        val c = card()
        c.addView(label("GIFTS FOR YOU", 13f, dim, true))
        for (i in 0 until minOf(10, gifts.length())) {
            val it = gifts.getJSONObject(i)
            val id = it.optInt("id")
            val kind = it.optString("kind")
            val title = it.optString("title")
            c.addView(spaced(label("🎁 $title · $kind · ${fmt(it.optDouble("ts", 0.0))}", 14f, warn, true)))
            it.optString("note").takeIf { n -> n.isNotBlank() && n != "null" }?.let { n -> c.addView(label("\"$n\"", 13f, textCol)) }
            when (kind) {
                "poem" -> {
                    val text = it.optString("text")
                    c.addView(label(text, 14f, cyan))
                    c.addView(rowOf(button("Keep / share", cyan) { shareText(title, text) }))
                }
                "song" -> {
                    val ref = it.optString("ref")
                    c.addView(rowOf(button("▶ Play", cyan) { playAudio("/api/compositions/$ref.wav") },
                        button("Save", dim) { bgTask({ a -> a.getBytes("/api/compositions/$ref.wav") }) { b -> saveAudio(b, "stellar-hub-song-$ref.wav") } }))
                }
                "painting", "curio" -> {
                    c.addView(remoteImage("/api/gifts/$id.png", 96))
                    c.addView(rowOf(button("Save to photos", cyan) {
                        bgTask({ a -> a.getBytes("/api/gifts/$id.png") }) { b ->
                            BitmapFactory.decodeByteArray(b, 0, b.size)?.let { bmp -> saveBitmap(bmp, "stellar-hub-gift-$id.png") }
                        }
                    }))
                }
            }
        }
        content.addView(c, 1)
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
                if (!isOwner && kind != "letter") { } else when (kind) {
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
        bgTask({ Triple(Triple(it.getObject("/api/colony"), it.getArray("/api/milestones"), it.getObject("/api/gallery")), it.getObject("/api/visitors"), it.getObject("/api/pets")) }) { (t, vis, pets) ->
            val (col, ms, gal) = t
            if (tab == "colony") { renderDigests(gal); renderEconomyCard(); renderPets(pets); renderVisitors(vis); renderColony(col, false); renderMilestones(ms); renderStudies(gal) }
        }
    }

    /** v0.13.3: the colony economy: this week's money in and out by category, plus warnings. */
    private fun renderEconomyCard() {
        val c = section("Colony economy")
        c.addView(label("Loading…", 12f, dim))
        val a = api ?: return
        io.execute {
            val e = try { a.getObject("/api/economy") } catch (ex: Exception) {
                main.post {
                    c.removeViews(1, c.childCount - 1)
                    c.addView(label(if (ex.message == "NEEDS_NEWER_HUB") "Update the hub to v0.13.3 or later to see this." else explain(ex), 12f, dim))
                }
                return@execute
            }
            main.post { if (!isFinishing) showEconomy(c, e) }
        }
    }

    private fun showEconomy(c: LinearLayout, e: JSONObject) {
        run {
            c.removeViews(1, c.childCount - 1)
            val w = e.optJSONObject("week") ?: JSONObject()
            c.addView(label("◈ ${e.optInt("balance")} · this week +${w.optInt("in")} / −${w.optInt("out")}", 15f, textCol, true))
            val warns = e.optJSONArray("warnings") ?: JSONArray()
            for (i in 0 until warns.length()) c.addView(label("⚠ ${warns.getString(i)}", 13f, warn))
            if (warns.length() == 0) c.addView(label("Nothing unusual.", 12f, good))
            val days = e.optJSONArray("days") ?: JSONArray()
            val n = days.length()
            if (n > 0) {         // a little 14-day picture: earned (green) and spent (red) per day
                val rowV = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.BOTTOM }
                var top = 10
                for (i in maxOf(0, n - 14) until n) days.getJSONObject(i).let { top = maxOf(top, it.optInt("in"), it.optInt("out")) }
                for (i in maxOf(0, n - 14) until n) {
                    val d = days.getJSONObject(i)
                    for ((v, col) in listOf(d.optInt("in") to good, d.optInt("out") to bad)) {
                        val bar = View(this).apply { setBackgroundColor(col) }
                        rowV.addView(bar, LinearLayout.LayoutParams(dp(7), maxOf(dp(1), dp(48) * v / top)).apply { marginEnd = dp(2) })
                    }
                    rowV.addView(View(this), LinearLayout.LayoutParams(dp(4), 1))
                }
                c.addView(spaced(rowV))
                c.addView(label("Last 14 days: earned (green) and spent (red)", 11f, dim))
            }
            val cats = w.optJSONObject("categories")
            val keys = ArrayList<String>()
            cats?.keys()?.forEach { keys.add(it) }
            keys.sortByDescending { k -> cats!!.getJSONObject(k).let { it.optInt("in") + it.optInt("out") } }
            for (k in keys) {
                val v = cats!!.getJSONObject(k)
                c.addView(label("$k · +${v.optInt("in")} / −${v.optInt("out")}", 13f, textCol))
            }
        }
    }

    private fun petBar(c: LinearLayout, name: String, v: Double, color: Int) {
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        row.addView(label(name, 12f, dim), LinearLayout.LayoutParams(dp(78), ViewGroup.LayoutParams.WRAP_CONTENT))
        val pb = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100; progress = v.toInt().coerceIn(0, 100)
            progressTintList = android.content.res.ColorStateList.valueOf(color)
        }
        row.addView(pb, LinearLayout.LayoutParams(0, dp(10), 1f))
        c.addView(row)
    }

    private fun renderPets(d: JSONObject) {
        val pets = d.optJSONArray("pets") ?: return
        val alive = (0 until pets.length()).map { pets.getJSONObject(it) }.filter { it.optString("status") in listOf("ok", "sick", "injured", "critical") }
        if (alive.isEmpty()) return
        val c = section("PETS")
        val credits = d.optInt("credits")
        if (credits < 0) c.addView(label("In debt: $credits credits. Nothing can be bought until it's paid back.", 13f, bad))
        val pal = lastPalette
        for (p in alive) {
            val status = p.optString("status")
            val head = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
            if (pal != null) p.optJSONArray("frames")?.optJSONArray(0)?.let { head.addView(pixelView(it, pal, 40)) }
            head.addView(label("  ${p.optString("name")} · ${p.optString("species_name")} · lv ${p.optInt("level", 1)} · $status", 15f,
                if (status == "ok") good else if (status == "critical") bad else warn, true))
            c.addView(spaced(head))
            if (status == "critical") c.addView(label("Critical! Rescue costs ${p.optInt("rescue")} credits; " +
                "${p.optDouble("hours_left", 0.0).toInt()} hours left before it's taken away.", 13f, bad))
            val job = p.optString("job").takeIf { it.isNotBlank() && it != "null" }
            c.addView(label((if (job != null) "Job: ${job.replace('_', ' ')} × ${p.optInt("shifts")}/day (safe ~${p.optInt("safe")})" else "Not trained yet") +
                " · ${p.optString("stage")} · ${if (p.optBoolean("on_shift")) "on shift" else "resting"}", 12f, dim))
            petBar(c, "health", p.optDouble("health"), good)
            petBar(c, "energy", p.optDouble("energy"), cyan)
            petBar(c, "fullness", 100 - p.optDouble("hunger"), warn)
            petBar(c, "happiness", p.optDouble("happiness"), pink)
            petBar(c, "strain", p.optDouble("strain"), bad)
        }
        val log = d.optJSONArray("log") ?: JSONArray()
        for (i in 0 until minOf(4, log.length())) {
            val l = log.getJSONObject(i)
            c.addView(spaced(label("${l.optString("name")} · ${fmt(l.optDouble("ts", 0.0))}", 12f, textCol, true)))
            c.addView(label(l.optString("text"), 12f, dim))
        }
    }

    private fun renderVisitors(vis: JSONObject) {
        val now = vis.optJSONObject("now")
        val visits = vis.optJSONArray("visits") ?: JSONArray()
        if (now == null && visits.length() == 0) return
        val c = section("VISITORS")
        if (now != null) c.addView(label("🧳 ${now.optString("name")}, ${now.optString("who")}, is at the " +
            "${names[now.optString("building")] ?: now.optString("building")} until ${fmt(now.optDouble("until", 0.0))}", 14f, warn))
        for (i in 0 until minOf(4, visits.length())) {
            val v = visits.getJSONObject(i)
            c.addView(spaced(label("${v.optString("visitor")} · ${fmt(v.optDouble("ts", 0.0))}", 13f, textCol, true)))
            c.addView(label(v.optString("talk"), 13f, dim))
            v.optString("learned").takeIf { it.isNotBlank() }?.let { c.addView(label(it, 13f, cyan)) }
        }
    }

    private fun renderMilestones(ms: JSONArray) {
        val s = lastStatus
        if (s != null) {
            val hb = section("HOBBIES & SKILLS")
            val hj = s.optJSONObject("hobbies")
            if (hj == null || hj.length() == 0) hb.addView(label("No hobbies yet. It picks them up as it tries things.", 13f, dim))
            hj?.let { h ->
                val ks = h.keys()
                while (ks.hasNext()) {
                    val k = ks.next()
                    val o = h.getJSONObject(k)
                    hb.addView(spaced(label("${hobbyIcons[k] ?: ""} $k · level ${o.optInt("level")} · ${o.optInt("xp")} xp", 14f)))
                    hb.addView(ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply { max = 100; progress = minOf(100, o.optInt("level") * 10) })
                }
            }
            val tr = section("PERSONALITY TRAITS")
            s.optJSONObject("traits")?.let { t ->
                val ks = t.keys()
                while (ks.hasNext()) {
                    val k = ks.next()
                    tr.addView(label("$k · ${t.optInt(k)}", 13f))
                    tr.addView(ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply { max = 100; progress = t.optInt(k) })
                }
            }
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

    private fun renderDigests(gal: JSONObject) {
        content.removeAllViews()
        content.addView(button("Refresh", panel) { loadColony() }.apply { setTextColor(textCol) })
        val ds = gal.optJSONArray("digests") ?: JSONArray()
        if (ds.length() > 0) {
            val d = ds.getJSONObject(0)
            val c = section("📰 THIS WEEK IN THE COLONY · ${d.optString("week")}")
            c.addView(label(d.optString("text"), 14f))
        }
    }

    private fun renderStudies(gal: JSONObject) {
        val qs = gal.optJSONArray("quizzes") ?: JSONArray()
        if (qs.length() == 0) return
        val c = section("ORBITAL STATION · STUDIES")
        for (i in 0 until qs.length()) {
            val q = qs.getJSONObject(i)
            c.addView(spaced(label("${q.optString("topic")} · ${q.optInt("mastery")}% mastered", 13f)))
            c.addView(ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply { max = 100; progress = q.optInt("mastery") })
        }
    }

    private fun renderColony(col: JSONObject, clear: Boolean = true) {
        if (clear) {
            content.removeAllViews()
            content.addView(button("Refresh", panel) { loadColony() }.apply { setTextColor(textCol) })
        }

        // Space events: start one, or stop the one that's happening
        val evc = section("SPACE EVENTS")
        val ev = lastStatus?.optJSONObject("event")
        evc.addView(label(if (ev != null) "${ev.optString("title")} until ${fmt(ev.optDouble("end", 0.0))}" else "Clear skies.", 14f, if (ev != null) warn else dim))
        if (ev != null) {
            evc.addView(rowOf(button("⏹ Stop event", bad) {
                bgTask({ it.post("/api/space_event/stop") }) { toast("The skies clear"); pollStatus(); main.postDelayed({ if (tab == "colony") loadColony() }, 800) }
            }))
        } else {
            val starts = listOf("meteor_shower" to "☄️ Meteors", "solar_storm" to "☀️ Storm", "eclipse" to "🌑 Eclipse", "trader" to "🛸 Trader")
            for (pair in starts.chunked(2)) {
                evc.addView(rowOf(*pair.map { (type, title) ->
                    button(title, cyan) {
                        bgTask({ it.post("/api/space_event", JSONObject().put("type", type)) }) { r ->
                            toast(if (r.optBoolean("ok", true)) "$title started" else "Another event is already happening")
                            pollStatus(); main.postDelayed({ if (tab == "colony") loadColony() }, 800)
                        }
                    }
                }.toTypedArray()))
            }
        }

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
        if (!col.optBoolean("sandbox")) fh.addView(label("Sandbox not installed on the hub: ${col.optString("sandbox_hint")}", 12f, warn))
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

    // ------------------------------------------------------------------ workshop (v0.13)
    private fun loadWorkshop() {
        loading()
        bgTask({ it.getObject("/api/workshop") }) { d -> if (tab == "build") renderWorkshop(d) }
    }

    private fun renderWorkshop(d: JSONObject) {
        content.removeAllViews()
        val head = section("Weekly goals")
        head.addView(label("Coding level ${d.optInt("code_level", 1)} · machine level ${d.optInt("mech_level", 1)} · skill notebook: ${d.optInt("skills")} entries", 12f, dim))
        val goals = d.optJSONArray("goals") ?: JSONArray()
        if (goals.length() == 0) head.addView(label("No goals yet. They arrive with the Fabrication Hangar and the Mechanical Workshop.", 13f, dim))
        for (i in 0 until goals.length()) {
            val g = goals.getJSONObject(i)
            val st = g.optString("status")
            val icon = when (g.optString("kind")) { "code" -> "💻"; "machine" -> "⚙️"; else -> "📐" }
            head.addView(spaced(label("$icon ${g.optString("title")}  ·  $st", 14f,
                when (st) { "passed" -> good; "missed", "cancelled" -> bad; else -> warn }, true)))
            head.addView(label("${if (g.optString("source") == "creator") "your goal" else "weekly"} · ${g.optInt("attempts")} tries · ${g.optString("text")}", 12f, dim))
            val code = g.optString("last_code").takeIf { it.isNotBlank() && it != "null" }
            if (code != null) head.addView(label(code.take(1200), 11f, textCol).apply { typeface = Typeface.MONOSPACE })
            val id = g.optInt("id")
            if (st == "review") head.addView(rowOf(
                smallButton("✓ Passed", good) { reviewGoal(id, true) }, smallButton("Not yet", bad) { reviewGoal(id, false) }))
            if (g.optString("source") == "creator" && (st == "open" || st == "review"))
                head.addView(rowOf(smallButton("Remove", line) {
                    bgTask({ it.post("/api/goals/cancel", JSONObject().put("id", id)) }) { loadWorkshop() } }))
        }

        val add = section("Give it a goal")
        add.addView(label("Coding goals with tests are checked automatically in the sandbox. Without tests, you review the answer.", 12f, dim))
        var kind = "code"
        val kinds = listOf("code" to "💻 Coding", "machine" to "⚙️ Machine", "plan" to "📐 Plan")
        val kindRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        fun paintKinds() { for (j in 0 until kindRow.childCount) (kindRow.getChildAt(j) as Button).setTextColor(if (kinds[j].first == kind) cyan else dim) }
        for ((k, t) in kinds) kindRow.addView(smallButton(t, line) { kind = k; paintKinds() })
        paintKinds()
        add.addView(kindRow)
        val title = input("Short title, like: Reverse a signal")
        val text = input("What should it make? Name the functions.", 3)
        val tests = input("Optional tests: assert reverse('abc') == 'cba'", 3).apply { typeface = Typeface.MONOSPACE }
        add.addView(spaced(title)); add.addView(spaced(text)); add.addView(spaced(tests))
        add.addView(rowOf(smallButton("Add goal", cyan) {
            val body = JSONObject().put("kind", kind).put("title", title.text.toString()).put("text", text.text.toString())
                .put("tests", tests.text.toString())
            bgTask({ it.post("/api/goals", body) }) { r ->
                if (r.optBoolean("ok")) { toast("Goal added"); loadWorkshop() } else toast(r.optString("error", "Couldn't add it"))
            }
        }))

        val mach = section("Machines & parts")
        val parts = d.optJSONObject("parts")
        val owned = ArrayList<String>()
        parts?.keys()?.forEach { k -> val n = parts.optInt(k); if (n > 0) owned.add("${k.replace('_', ' ')} ×$n") }
        mach.addView(label("Parts: ${if (owned.isEmpty()) "none yet" else owned.joinToString(", ")}", 12f, dim))
        val ms = d.optJSONArray("machines") ?: JSONArray()
        for (i in 0 until ms.length()) {
            val m = ms.getJSONObject(i)
            val cond = m.optDouble("condition")
            mach.addView(spaced(label("⚙️ ${m.optString("name")}  ·  ${if (cond <= 0) "broken" else "${cond.roundToInt()}%"}", 14f,
                if (cond <= 0) bad else if (cond < 30) warn else good, true)))
            mach.addView(label("It ${m.optString("does")}.", 12f, dim))
        }
        if (ms.length() == 0) mach.addView(label("No machines yet.", 13f, dim))

        val plans = section("Real-world plans")
        plans.addView(label("About once a week your resident designs a small low-voltage project for you to build.", 12f, dim))
        val ps = d.optJSONArray("plans") ?: JSONArray()
        if (ps.length() == 0) plans.addView(label("No plans yet. They start once the Mechanical Workshop is built.", 13f, dim))
        for (i in 0 until ps.length()) {
            val p = ps.getJSONObject(i)
            val q = p.optJSONObject("plan") ?: JSONObject()
            val pid = p.optInt("id")
            plans.addView(spaced(label("📐 ${p.optString("title")}", 15f, textCol, true)))
            plans.addView(label("${p.optString("kind").replace('_', ' ')} · ${q.optString("difficulty")} · ${fmt(p.optDouble("ts"))}", 12f, dim))
            plans.addView(label(q.optString("safety"), 12f, bad))
            plans.addView(label(q.optString("summary"), 13f, textCol))
            val btns = arrayListOf<View>(smallButton("⬇ Plan", cyan) { savePlanFile(pid, "md") })
            if (q.optString("code").isNotBlank()) btns.add(smallButton("⬇ Code", line) { savePlanFile(pid, "code") })
            if (q.optString("scad").isNotBlank()) btns.add(smallButton("⬇ OpenSCAD", line) { savePlanFile(pid, "scad") })
            plans.addView(rowOf(*btns.toTypedArray()))
        }
    }

    private fun reviewGoal(id: Int, passed: Boolean) {
        bgTask({ it.post("/api/goals/review", JSONObject().put("id", id).put("passed", passed)) }) { loadWorkshop() }
    }

    /** Saves a plan (or its code / OpenSCAD file) into Downloads/Stellar Hub. */
    private fun savePlanFile(pid: Int, part: String) {
        bgTask({ it.getBytes("/api/plans/$pid.$part") }) { bytes ->
            val text = String(bytes, Charsets.UTF_8)
            val ext = when (part) { "md" -> "md"; "scad" -> "scad"; else -> if ("void setup" in text || "#include" in text) "ino" else "py" }
            val name = "stellar_plan_${pid}_${part}.$ext"
            try {
                if (Build.VERSION.SDK_INT >= 29) {
                    val values = ContentValues().apply {
                        put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                        put(MediaStore.MediaColumns.MIME_TYPE, "text/plain")
                        put(MediaStore.MediaColumns.RELATIVE_PATH, "Download/Stellar Hub")
                    }
                    val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                        ?: throw IllegalStateException("no storage")
                    contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
                    toast("Saved to Download/Stellar Hub")
                } else {
                    val dir = getExternalFilesDir("Download") ?: filesDir
                    java.io.File(dir, name).writeBytes(bytes)
                    toast("Saved to ${dir.absolutePath}")
                }
            } catch (e: Exception) {
                toast("Couldn't save it: ${e.message}")
            }
        }
    }

    private fun loadGallery() {
        loading()
        bgTask({ Triple(Triple(it.getObject("/api/gallery"), it.getObject("/api/chess"), it.getObject("/api/exchange")), it.getObject("/api/album"), it.getObject("/api/museum")) }) { (t, album, museum) ->
            val (gal, ch, ex) = t
            if (tab == "gallery") { renderGallery(gal, ch); renderMuseum(museum); renderAlbum(album); renderExchange(ex) }
        }
    }

    private fun pixelView(rows: JSONArray, pal: Map<Char, Int>, sizeDp: Int): ImageView = ImageView(this).apply {
        val n = maxOf(1, rows.length())
        setImageBitmap(Pixel.bitmap(rows, pal, maxOf(1, dp(sizeDp) / n), Color.parseColor("#080A18")))
        layoutParams = LinearLayout.LayoutParams(dp(sizeDp), dp(sizeDp)).apply { setMargins(dp(3), dp(3), dp(3), dp(3)) }
    }

    /** Lays views out in rows of `perRow`. */
    private fun gridInto(parent: LinearLayout, items: List<View>, perRow: Int) {
        var row: LinearLayout? = null
        items.forEachIndexed { i, v ->
            if (i % perRow == 0) {
                row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
                parent.addView(row)
            }
            row?.addView(v)
        }
    }

    private fun renderMuseum(m: JSONObject) {
        val c = section("CURIO SETS & THE MUSEUM")
        c.addView(label("Reputation ${m.optInt("reputation")} · daily stipend ${m.optInt("stipend")} credits · " +
            "${m.optJSONArray("exhibits")?.length() ?: 0} exhibits", 13f, warn))
        val pal = lastPalette
        val sets = m.optJSONArray("sets") ?: JSONArray()
        val list = (0 until sets.length()).map { sets.getJSONObject(it) }.sortedByDescending { it.optInt("have").toDouble() / it.optInt("need", 1) }
        for (s in list) {
            val have = s.optInt("have"); val need = s.optInt("need")
            if (have == 0 && list.indexOf(s) > 7) continue
            c.addView(spaced(label("${s.optString("name")} · ${s.optString("rarity")} · $have/$need · from ${s.optString("source")}",
                13f, if (have == need) good else textCol, true)))
            if (pal != null) {
                val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
                val pieces = s.optJSONArray("pieces") ?: JSONArray()
                for (i in 0 until pieces.length()) {
                    val p = pieces.getJSONObject(i)
                    row.addView(pixelView(p.getJSONArray("icon"), pal, 28).apply { alpha = if (p.optInt("owned") > 0) 1f else 0.25f })
                }
                c.addView(row)
            }
            c.addView(label("Donate +${s.optInt("value")} reputation, or sell for ${s.optInt("sale")}", 12f, dim))
        }
    }

    private fun renderAlbum(album: JSONObject) {
        val photos = album.optJSONArray("album") ?: return
        val c = section("PHOTO ALBUM")
        if (photos.length() == 0) { c.addView(label("Its first snapshots will show up here.", 13f, dim)); return }
        for (i in 0 until minOf(12, photos.length())) {
            val p = photos.getJSONObject(i)
            val id = p.optInt("id")
            c.addView(spaced(remoteImage("/api/album/$id.png", 140)))
            c.addView(label("${p.optString("title")} · ${fmt(p.optDouble("ts", 0.0))}", 12f, dim))
            c.addView(rowOf(button("Save", dim) {
                bgTask({ a -> a.getBytes("/api/album/$id.png") }) { b ->
                    BitmapFactory.decodeByteArray(b, 0, b.size)?.let { bmp -> saveBitmap(bmp, "stellar-hub-album-$id.png") }
                }
            }.apply { textSize = 12f }))
        }
    }

    private fun renderGallery(gal: JSONObject, ch: JSONObject) {
        content.removeAllViews()
        content.addView(button("Refresh", panel) { loadGallery() }.apply { setTextColor(textCol) })
        val pal = Pixel.palette(gal.getJSONObject("palette"))

        // Home showcase
        val hs = section("HOME DOME SHOWCASE")
        val floors = gal.optJSONArray("home_floors") ?: JSONArray()
        for (f in 0 until floors.length()) {
            val spots = floors.getJSONArray(f)
            var used = 0
            val views = ArrayList<View>()
            for (i in 0 until spots.length()) {
                if (spots.isNull(i)) {
                    views.add(label("${i + 1}", 11f, dim).apply {
                        gravity = Gravity.CENTER
                        background = GradientDrawable().apply { setStroke(dp(1), line); cornerRadius = dp(6).toFloat() }
                        layoutParams = LinearLayout.LayoutParams(dp(44), dp(44)).apply { setMargins(dp(3), dp(3), dp(3), dp(3)) }
                    })
                } else {
                    used++
                    val sp = spots.getJSONObject(i)
                    val rows = sp.optJSONArray("rows") ?: sp.optJSONArray("icon") ?: JSONArray().put("..")
                    views.add(pixelView(rows, pal, 44))
                }
            }
            hs.addView(spaced(label("Floor ${f + 1} · $used/12", 12f, dim, true)))
            gridInto(hs, views, 6)
        }

        // Paintings
        val pg = section("STARLIGHT GALLERY · PAINTINGS")
        val ps = gal.optJSONArray("paintings") ?: JSONArray()
        if (ps.length() == 0) pg.addView(label("No paintings yet.", 13f, dim))
        val pViews = ArrayList<View>()
        for (i in 0 until ps.length()) {
            val p = ps.getJSONObject(i)
            val cell = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL }
            cell.addView(pixelView(p.getJSONArray("rows"), pal, 96))
            cell.addView(label(p.optString("title").take(18), 11f, textCol).apply { gravity = Gravity.CENTER })
            cell.setOnClickListener { toast(p.optString("about")) }
            pViews.add(cell)
        }
        gridInto(pg, pViews, 3)

        // Songs
        val sg = section("RADIO STUDIO · SONGS")
        val cs = gal.optJSONArray("compositions") ?: JSONArray()
        if (cs.length() == 0) sg.addView(label("No songs yet.", 13f, dim))
        for (i in 0 until cs.length()) {
            val c = cs.getJSONObject(i)
            val id = c.getInt("id")
            sg.addView(rowOf(button("▶", cyan) { playSong(id) },
                label("${c.optString("title")} · ${c.optInt("bpm")} bpm · ${c.optDouble("seconds", 0.0).toInt()}s", 14f)))
        }
        sg.addView(rowOf(button("■ Stop", dim) { player?.release(); player = null }))

        // Writings
        val wr = section("LOW-G PARK · WRITINGS")
        val ws = gal.optJSONArray("writings") ?: JSONArray()
        if (ws.length() == 0) wr.addView(label("Nothing written yet.", 13f, dim))
        for (i in 0 until minOf(15, ws.length())) {
            val w = ws.getJSONObject(i)
            wr.addView(spaced(label("${w.optString("title")} · ${w.optString("kind")}", 14f, textCol, true)))
            wr.addView(label(w.optString("text"), 13f, dim))
        }

        // Curios
        val cu = section("CURIO COLLECTION")
        val cl = gal.optJSONArray("curios") ?: JSONArray()
        cu.addView(label("${cl.length()} of ${gal.optInt("curio_total", 128)} found", 13f, dim))
        val info = label("Tap a curio to read about it.", 13f, dim)
        val cViews = ArrayList<View>()
        for (i in 0 until cl.length()) {
            val c = cl.getJSONObject(i)
            cViews.add(pixelView(c.getJSONArray("sprite"), pal, 44).apply {
                setOnClickListener {
                    val sb = StringBuilder("${c.optString("name")} · ${c.optString("rarity")}")
                    if (c.optInt("count") > 1) sb.append(" · ×${c.optInt("count")}")
                    sb.append("\n").append(c.optString("about"))
                    val note = c.optString("note")
                    if (note.isNotBlank()) sb.append("\n\n\"").append(note).append("\"")
                    val found = c.optString("found")
                    if (found.isNotBlank()) sb.append("\nFirst found: ").append(found)
                    info.text = sb.toString()
                    info.setTextColor(textCol)
                }
            })
        }
        gridInto(cu, cViews, 6)
        cu.addView(spaced(info))

        renderChessCard(ch)
    }

    private fun renderExchange(ex: JSONObject) {
        val c = section("CURIO EXCHANGE")
        c.addView(label("Trade up: 5 spares → 1 of the next rarity. Anything on display is never sold.", 12f, dim))
        val wanted = ex.optJSONArray("wanted") ?: JSONArray()
        c.addView(spaced(label("Today's wanted board", 13f, textCol, true)))
        for (i in 0 until wanted.length()) {
            val o = wanted.getJSONObject(i)
            c.addView(label("${o.optString("collector")} wants ${o.optString("name")} (${o.optString("rarity")}) for ◈ ${o.optInt("price")}" +
                if (o.optBoolean("spare")) "  ✓ has a spare" else "", 13f, if (o.optBoolean("spare")) good else textCol))
        }
        val au = ex.optJSONArray("auctions") ?: JSONArray()
        if (au.length() > 0) c.addView(spaced(label("Auctions", 13f, textCol, true)))
        for (i in 0 until au.length()) {
            val x = au.getJSONObject(i)
            val st = x.optString("status")
            val info = if (st == "open") "closes ${fmt(x.optDouble("end_ts", 0.0))}" else "best bid ${x.optInt("best_bid")}"
            c.addView(label("${x.optString("name")} · $st · reserve ${x.optInt("reserve")} · $info", 13f,
                when (st) { "sold" -> good; "open" -> warn; else -> dim }))
        }
        val tr = ex.optJSONArray("trades") ?: JSONArray()
        if (tr.length() > 0) c.addView(spaced(label("Recent trades", 13f, textCol, true)))
        for (i in 0 until minOf(8, tr.length())) {
            val t = tr.getJSONObject(i)
            val cr = t.optInt("credits")
            c.addView(label("${t.optString("kind").replace('_', ' ')}: ${t.optString("detail")}" + if (cr > 0) "  +$cr" else "", 12f, dim))
        }
    }

    private fun playSong(id: Int) = playAudio("/api/compositions/$id.wav")

    /** Streams a WAV from the hub (songs, spoken logs, radio shows, chat voice). */
    private fun playAudio(path: String) {
        val a = api ?: return
        player?.release()
        player = MediaPlayer().apply {
            try {
                setDataSource(this@MainActivity, Uri.parse(a.base + path),
                    mapOf("X-Hub-Token" to (prefs.getString("code", "") ?: "").trim().uppercase()))
                setOnPreparedListener { it.start() }
                setOnErrorListener { _, _, _ -> toast("Couldn't play that"); true }
                prepareAsync()
            } catch (e: Exception) {
                toast("Couldn't play that")
            }
        }
    }

    override fun onDestroy() {
        side.shutdownNow()
        player?.release()
        player = null
        super.onDestroy()
    }

    private val pieces = mapOf('K' to "♚", 'Q' to "♛", 'R' to "♜", 'B' to "♝", 'N' to "♞", 'P' to "♟")

    private fun renderChessCard(ch: JSONObject) {
        val card = section("CHESS AT THE PARK")
        val g = ch.optJSONObject("game")
        if (g == null) {
            card.addView(label("No game yet. Your resident plays at the park's chess tables.", 13f, dim))
        } else {
            val board = g.optString("board")
            val creator = g.optString("creator", "w")
            val legal = g.optJSONArray("legal") ?: JSONArray()
            val legalList = (0 until legal.length()).map { legal.getString(it) }
            val result = g.optString("result").takeIf { it.isNotBlank() && it != "null" }
            val last = g.optString("last").takeIf { it.isNotBlank() && it != "null" }
            val yourTurn = result == null && g.optString("turn") == creator
            val status = when {
                result != null -> mapOf("1-0" to "White wins", "0-1" to "Black wins").getOrElse(result) { "Draw" }
                yourTurn -> if (g.optBoolean("check")) "Your move (you're in check!)" else "Your move"
                else -> "Your resident is thinking…"
            }
            card.addView(label(status, 14f, if (yourTurn) warn else textCol, true))
            g.optJSONArray("comments")?.let { cm ->
                if (cm.length() > 0) card.addView(label("\"" + cm.getJSONObject(cm.length() - 1).optString("text") + "\"", 13f, cyan))
            }
            val flip = creator == "b"
            val targets = chessSel?.let { sel -> legalList.filter { it.startsWith(sel) }.map { it.substring(2, 4) } } ?: emptyList()
            val size = (resources.displayMetrics.widthPixels - dp(60)) / 8
            for (r in 0 until 8) {
                val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
                for (c in 0 until 8) {
                    val rr = if (flip) 7 - r else r
                    val cc = if (flip) 7 - c else c
                    val name = "abcdefgh"[cc].toString() + (8 - rr)
                    val p = board[rr * 8 + cc]
                    val base = if ((rr + cc) % 2 == 1) Color.parseColor("#232A52") else Color.parseColor("#3A4060")
                    val bg = when {
                        name == chessSel -> warn
                        name in targets -> Color.parseColor("#1F8FB3")
                        last != null && (last.startsWith(name) || last.substring(2, 4) == name) -> Color.parseColor("#5B3FB5")
                        else -> base
                    }
                    row.addView(TextView(this).apply {
                        text = if (p == '.') "" else pieces[p.uppercaseChar()]
                        textSize = 22f
                        gravity = Gravity.CENTER
                        setTextColor(if (p.isUpperCase()) Color.WHITE else Color.parseColor("#0B0D17"))
                        setBackgroundColor(bg)
                        setOnClickListener {
                            if (!yourTurn) return@setOnClickListener
                            val sel = chessSel
                            val mv = if (sel != null) legalList.firstOrNull { it.startsWith(sel + name) && (it.length == 4 || it.endsWith("q")) } else null
                            if (mv != null) {
                                chessSel = null
                                toast("Your resident is thinking…")
                                bgTask({ it.post("/api/chess/move", JSONObject().put("move", mv)) }) { loadGallery() }
                            } else {
                                chessSel = if (legalList.any { it.startsWith(name) }) name else null
                                loadGallery()
                            }
                        }
                    }, LinearLayout.LayoutParams(size, size))
                }
                card.addView(row)
            }
        }
        card.addView(rowOf(
            button("New game (white)", cyan) { chessSel = null; bgTask({ it.post("/api/chess/new", JSONObject().put("color", "white")) }) { loadGallery() } },
            button("(black)", dim) { chessSel = null; bgTask({ it.post("/api/chess/new", JSONObject().put("color", "black")) }) { loadGallery() } }
        ))
    }

    private fun savePhoto() {
        val bmp: Bitmap = town.snapshot() ?: run { toast("The colony hasn't loaded yet"); return }
        saveBitmap(bmp, "stellar-hub-${System.currentTimeMillis()}.png")
    }

    private fun saveBitmap(bmp: Bitmap, name: String) {
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                    put(MediaStore.MediaColumns.MIME_TYPE, "image/png")
                    put(MediaStore.MediaColumns.RELATIVE_PATH, "Pictures/Stellar Hub")
                }
                val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
                    ?: throw IllegalStateException("no storage")
                contentResolver.openOutputStream(uri)?.use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
                toast("Saved to Pictures/Stellar Hub")
            } else {
                val dir = getExternalFilesDir("Pictures") ?: filesDir
                java.io.File(dir, name).outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
                toast("Saved to ${dir.absolutePath}")
            }
        } catch (e: Exception) {
            toast("Couldn't save the photo: ${e.message}")
        }
    }

    private fun saveAudio(bytes: ByteArray, name: String) {
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                    put(MediaStore.MediaColumns.MIME_TYPE, "audio/wav")
                    put(MediaStore.MediaColumns.RELATIVE_PATH, "Music/Stellar Hub")
                }
                val uri = contentResolver.insert(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, values)
                    ?: throw IllegalStateException("no storage")
                contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
                toast("Saved to Music/Stellar Hub")
            } else {
                val dir = getExternalFilesDir("Music") ?: filesDir
                java.io.File(dir, name).writeBytes(bytes)
                toast("Saved to ${dir.absolutePath}")
            }
        } catch (e: Exception) {
            toast("Couldn't save it: ${e.message}")
        }
    }

    private fun shareText(title: String, text: String) {
        startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType("text/plain")
            .putExtra(Intent.EXTRA_SUBJECT, title).putExtra(Intent.EXTRA_TEXT, "$title\n\n$text"), "Keep this poem"))
    }

    /** A PNG from the hub, shown in an ImageView once it arrives. */
    private fun remoteImage(path: String, heightDp: Int): ImageView = ImageView(this).apply {
        adjustViewBounds = true
        scaleType = ImageView.ScaleType.FIT_CENTER
        minimumHeight = dp(heightDp)
        val a = api ?: return@apply
        side.execute {
            try {
                val b = a.getBytes(path)
                val bmp = BitmapFactory.decodeByteArray(b, 0, b.size)
                main.post { setImageBitmap(bmp); (drawable as? android.graphics.drawable.BitmapDrawable)?.isFilterBitmap = false }
            } catch (e: Exception) { }
        }
    }

    private fun loadFeed() {
        loading()
        bgTask({ Pair(it.getArray("/api/feed?limit=60"), it.getObject("/api/audio")) }) { (arr, aud) -> if (tab == "feed") renderFeed(arr, aud) }
    }

    private fun renderFeed(arr: JSONArray, aud: JSONObject) {
        content.removeAllViews()
        content.addView(button("Refresh", panel) { loadFeed() }.apply { setTextColor(textCol) })
        val clips = aud.optJSONArray("audio") ?: JSONArray()
        if (clips.length() > 0) {
            val rc = section("RADIO · SHOWS & SPOKEN LOGS")
            for (i in 0 until minOf(8, clips.length())) {
                val a = clips.getJSONObject(i)
                rc.addView(spaced(label("${a.optString("title")} · ${fmt(a.optDouble("ts", 0.0))}", 13f, textCol, true)))
                rc.addView(label(a.optString("text").take(200), 12f, dim))
                if (a.optString("status") == "ready") {
                    val id = a.optInt("id")
                    rc.addView(rowOf(button("▶ Play", cyan) { playAudio("/api/audio/$id.wav") },
                        button("Save", dim) { bgTask({ it.getBytes("/api/audio/$id.wav") }) { b -> saveAudio(b, "stellar-hub-log-$id.wav") } }))
                }
            }
        }
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
            val human = m.optString("who") == "creator"
            val speaker = m.optString("name").takeIf { it.isNotBlank() && it != "null" }
            val me = prefs.getString("username", "") ?: ""
            val mine = human && (speaker == null || speaker.equals(me, true) || (isOwner && speaker == lastStatus?.optString("creator")))
            c.addView(spaced(label(if (mine) "You" else if (human) speaker!! else (lastStatus?.optString("name") ?: "Resident"), 12f,
                if (mine) warn else if (human) pink else cyan, true)))
            c.addView(label(m.optString("text"), 15f))
            if (!human) {
                val n = i
                c.addView(button("🔊 Hear it", dim) { toast("Getting its voice…"); playAudio("/api/chat/voice/$n.wav") }.apply { textSize = 12f })
            }
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

        val sc = card()
        sc.addView(label("ASK WHAT IT REMEMBERS", 13f, dim, true))
        val qbox = input("e.g. What do you remember about the trader?")
        sc.addView(spaced(qbox))
        val answer = label("", 14f, cyan)
        sc.addView(rowOf(button("Ask", cyan) {
            val q = qbox.text.toString().trim()
            if (q.isEmpty()) return@button
            answer.text = "Remembering…"
            bgTask({ it.post("/api/search", JSONObject().put("q", q)) }) { r ->
                val mems = r.optJSONArray("memories") ?: JSONArray()
                val sb = StringBuilder(r.optString("answer"))
                for (i in 0 until minOf(4, mems.length())) {
                    val m = mems.getJSONObject(i)
                    sb.append("\n\n• ").append(fmt(m.optDouble("ts", 0.0))).append(": ").append(m.optString("text").take(200))
                }
                answer.text = sb.toString()
            }
        }))
        sc.addView(spaced(answer))
        content.addView(sc)

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
        // Connection: address + pair code, then create a username and wait for the owner's approval
        val conn = card()
        conn.addView(label("Connection", 13f, dim, true))
        val signedIn = (prefs.getString("code", "") ?: "").isNotBlank()
        val uname = prefs.getString("username", "") ?: ""
        if (signedIn && prefs.getString("join_status", "") != "pending") {
            conn.addView(label("Signed in as $uname · ${myRole}", 15f, good, true))
            conn.addView(label(when (myRole) {
                "owner" -> "You can do everything: approve requests and programs, change settings, and manage other people's devices."
                "member" -> "You can watch, chat, give goals, write letters and take a turn. The owner handles approvals and settings."
                else -> "You can watch the colony. Ask the owner if you'd like to chat too."
            }, 12f, dim))
            conn.addView(rowOf(smallButton("Refresh", line) { refreshMe { showTab("hub") } },
                smallButton("Sign out", bad) {
                    prefs.edit().remove("code").remove("username").remove("role").remove("join_status").apply()
                    connectFromPrefs(); showTab("hub")
                }))
        } else if (signedIn) {
            conn.addView(label("Waiting for approval", 15f, warn, true))
            conn.addView(label("“$uname” has asked to join. The owner approves it on the Stellar Hub dashboard (Hub tab → People & devices) or in their app.", 13f, dim))
            conn.addView(rowOf(smallButton("Check again", cyan) {
                bgTask({ it.getObject("/api/me") }) { me ->
                    prefs.edit().putString("role", me.optString("role")).putString("join_status", me.optString("status")).apply()
                    if (me.optString("status") == "active") { toast("Approved! Welcome, $uname"); pollStatus(); Notifier.schedule(this) }
                    showTab("hub")
                }
            }, smallButton("Start over", bad) {
                prefs.edit().remove("code").remove("join_status").apply(); connectFromPrefs(); showTab("hub")
            }))
        } else {
            conn.addView(label("Step 1 · Find these on the Stellar Hub dashboard, under “Hub Connect S · phone pairing”.", 13f, dim))
            val addr = input("Address, e.g. 100.101.102.103:8080", value = prefs.getString("address", "") ?: "")
            val code = input("Pair code, e.g. ABCD-EFGH-JKMN", value = prefs.getString("pair_code", "") ?: "").apply {
                inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS
            }
            conn.addView(spaced(addr)); conn.addView(spaced(code))
            conn.addView(spaced(label("Step 2 · Create your username", 14f, textCol, true)))
            conn.addView(label("This is how the resident will know you. 3-20 letters, numbers or spaces.", 12f, dim))
            val name = input("Username", value = uname)
            conn.addView(spaced(name))
            var another = false
            val anotherBtn = smallButton("☐ This is another device of mine", line) { }
            anotherBtn.setOnClickListener {
                another = !another
                anotherBtn.text = if (another) "☑ This is another device of mine" else "☐ This is another device of mine"
            }
            conn.addView(rowOf(anotherBtn))
            val msg = label("", 13f, bad)
            conn.addView(msg)
            conn.addView(rowOf(button("Join", cyan) {
                val address = addr.text.toString().trim()
                val pc = code.text.toString().trim().uppercase()
                val n = name.text.toString().trim()
                if (address.isBlank() || pc.isBlank()) { msg.text = "Enter the address and pair code first."; return@button }
                prefs.edit().putString("address", address).putString("pair_code", pc).apply()
                msg.setTextColor(dim); msg.text = "Checking…"
                val body = JSONObject().put("code", pc).put("name", n).put("another_device", another)
                    .put("platform", "${Build.MANUFACTURER} ${Build.MODEL}".trim())
                io.execute {
                    val r = try { Api(address, "").join(body) } catch (e: Exception) { JSONObject().put("ok", false).put("error", explain(e)) }
                    main.post {
                        if (!r.optBoolean("ok")) { msg.setTextColor(bad); msg.text = r.optString("error", "Couldn't join") }
                        else {
                            prefs.edit().putString("code", r.optString("token")).putString("username", r.optString("name"))
                                .putString("join_status", "pending").putString("role", "member").putInt("last_event", -1).apply()
                            connectFromPrefs()
                            toast("Asked to join as ${r.optString("name")}")
                            showTab("hub")
                        }
                    }
                }
            }))
        }
        content.addView(conn)
        if (isOwner && signedIn && prefs.getString("join_status", "") != "pending") content.addView(devicesCard())

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
        if (isOwner) {
            content.addView(phoneMusicCard())
            content.addView(listeningCard())
        }
        if (isOwner) content.addView(monitorCard())

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
        res.addView(rowOf(button(if (s.optBoolean("busy")) "Thinking…" else "Take a turn now", cyan) { takeTurn() }))
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

    // ------------------------------------------------------------------ phone music (Stellar Disc)
    private val discPackage = "com.stellapp.disc"
    private val audioPermission get() =
        if (Build.VERSION.SDK_INT >= 33) "android.permission.READ_MEDIA_AUDIO" else "android.permission.READ_EXTERNAL_STORAGE"

    /** Owner only: approve new phones, change roles, remove devices. */
    private fun devicesCard(): LinearLayout {
        val c = card()
        c.addView(label("People & devices", 13f, dim, true))
        c.addView(label("Member: watch, chat, give goals and letters, take a turn. Viewer: watch only.", 12f, dim))
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        c.addView(list)
        fun change(id: Int, body: JSONObject) { bgTask({ it.post("/api/devices/$id", body) }) { showTab("hub") } }
        bgTask({ it.getObject("/api/devices") }) { d ->
            val ds = d.optJSONArray("devices") ?: JSONArray()
            if (ds.length() == 0) list.addView(label("No phones yet.", 13f, dim))
            for (i in 0 until ds.length()) {
                val dv = ds.getJSONObject(i)
                val id = dv.optInt("id")
                val pending = dv.optString("status") == "pending"
                list.addView(spaced(label("📱 ${dv.optString("name")} · ${if (pending) "waiting" else dv.optString("role")}", 14f,
                    if (pending) warn else textCol, true)))
                list.addView(label(dv.optString("platform").ifBlank { "phone" } + if (pending) "" else " · last seen ${fmt(dv.optDouble("last_seen"))}", 12f, dim))
                if (pending) list.addView(rowOf(
                    smallButton("Approve as member", good) { change(id, JSONObject().put("status", "active").put("role", "member")) },
                    smallButton("Viewer", cyan) { change(id, JSONObject().put("status", "active").put("role", "viewer")) },
                    smallButton("Decline", bad) { change(id, JSONObject().put("status", "removed")) }))
                else list.addView(rowOf(
                    *listOf("owner", "member", "viewer").filter { it != dv.optString("role") }.map { r ->
                        smallButton("Make $r", line) { change(id, JSONObject().put("role", r)) } }.toTypedArray(),
                    smallButton("Remove", bad) { change(id, JSONObject().put("status", "removed")) }))
            }
        }
        return c
    }

    private fun discInstalled(): Boolean = try {
        packageManager.getPackageInfo(discPackage, 0); true
    } catch (e: PackageManager.NameNotFoundException) { false }

    private fun phoneMusicCard(): LinearLayout {
        val c = card()
        c.addView(label("Phone music · Stellar Disc", 13f, dim, true))
        c.addView(label("Share the song list from your phone with your resident. At the Radio Tower it can pick one, " +
            "and Stellar Disc plays it on your phone, only while Hub Connect S is open. Only titles, artists and " +
            "albums are sent to your hub, never the files.", 13f, dim))
        val on = prefs.getBoolean("share_music", false)
        if (!discInstalled()) c.addView(spaced(label("Stellar Disc isn't installed on this phone yet.", 13f, warn)))
        val info = lastStatus?.optJSONObject("phone_music")
        if (on && info != null) c.addView(spaced(label("${info.optInt("songs")} songs shared · updated ${fmt(info.optDouble("ts", 0.0))}", 13f, good)))
        if (on) {
            c.addView(rowOf(
                button("Update song list", cyan) { shareMusic(true) },
                button("Stop sharing", dim) {
                    prefs.edit().putBoolean("share_music", false).apply()
                    bgTask({ it.post("/api/phone/forget") }) { toast("Your phone's song list was removed from the hub"); pollStatusThenHub() }
                }))
        } else {
            c.addView(rowOf(button("Share my music", cyan) {
                prefs.edit().putBoolean("share_music", true).apply()
                shareMusic(true)
            }))
        }
        return c
    }

    private var monTrack = ""

    private fun monitorCard(): LinearLayout {
        val c = card()
        c.addView(label("MONITOR", 13f, dim, true))
        c.addView(label("Flags anything unusual with pets, money or the model. Alerts also come as notifications.", 12f, dim))
        val filters = listOf("" to "All", "pets" to "🐾 Pets", "money" to "◈ Money", "model" to "🧠 Model")
        c.addView(rowOf(*filters.map { (t, l) ->
            button(l, if (t == monTrack) cyan else dim) { monTrack = t; showTab("hub") }.apply { textSize = 12f }
        }.toTypedArray()))
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        c.addView(list)
        bgTask({ it.getObject("/api/monitor" + if (monTrack.isNotEmpty()) "?track=$monTrack" else "") }) { d ->
            val m = d.optJSONObject("model")
            if (m != null) list.addView(label("Model ${m.optString("model")}: ${m.optInt("calls_today")}/${m.optInt("call_limit")} AI calls today, " +
                "average turn ${m.optString("avg_turn_seconds")}s", 12f, textCol))
            val es = d.optJSONArray("entries") ?: JSONArray()
            if (es.length() == 0) list.addView(label("Nothing flagged. All quiet.", 13f, good))
            for (i in 0 until minOf(15, es.length())) {
                val e = es.getJSONObject(i)
                val lvl = e.optString("level")
                val icon = mapOf("pets" to "🐾", "money" to "◈", "model" to "🧠")[e.optString("track")] ?: ""
                list.addView(spaced(label("$icon ${e.optString("title")} · ${fmt(e.optDouble("ts", 0.0))}", 13f,
                    when (lvl) { "alert" -> bad; "warn" -> warn; else -> textCol }, true)))
                e.optString("detail").takeIf { it.isNotBlank() }?.let { list.addView(label(it, 12f, dim)) }
            }
        }
        return c
    }

    private fun listeningCard(): LinearLayout {
        val c = card()
        c.addView(label("Listening · Stellar Disc", 13f, dim, true))
        c.addView(label("Let your resident learn your music taste from what you play, finish and skip in Stellar Disc, " +
            "and listen along while this app is open. Turn on \"Share listening with Hub Connect S\" in Stellar Disc's " +
            "Settings too. Only song titles and artists are shared.", 13f, dim))
        val on = prefs.getBoolean("share_listening", false)
        c.addView(rowOf(button(if (on) "Listening sharing: ON" else "Listening sharing: OFF", if (on) good else cyan) {
            prefs.edit().putBoolean("share_listening", !on).apply()
            if (on) prefs.edit().putString("listen_queue", "[]").apply()
            showTab("hub")
        }))
        return c
    }

    /** Reads the song list from the phone's media library and sends it to the hub. */
    private fun shareMusic(announce: Boolean) {
        if (checkSelfPermission(audioPermission) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(audioPermission), 7)
            return
        }
        val a = api ?: run { toast("Set up the connection first"); return }
        if (announce) toast("Reading your music…")
        side.execute {
            try {
                val tracks = JSONArray()
                val cols = arrayOf(MediaStore.Audio.Media.TITLE, MediaStore.Audio.Media.ARTIST, MediaStore.Audio.Media.ALBUM)
                contentResolver.query(MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, cols,
                    MediaStore.Audio.Media.IS_MUSIC + " != 0", null, MediaStore.Audio.Media.TITLE + " ASC")?.use { cur ->
                    while (cur.moveToNext() && tracks.length() < 5000) {
                        val title = cur.getString(0) ?: continue
                        val artist = cur.getString(1)?.takeIf { it != "<unknown>" } ?: ""
                        tracks.put(JSONObject().put("title", title).put("artist", artist).put("album", cur.getString(2) ?: ""))
                    }
                }
                val r = a.post("/api/phone/music", JSONObject().put("tracks", tracks))
                prefs.edit().putLong("music_synced", System.currentTimeMillis()).apply()
                main.post {
                    if (isFinishing) return@post
                    if (announce) toast("Shared ${r.optInt("songs")} songs with your resident")
                    pollStatusThenHub()
                }
            } catch (e: Exception) {
                val why = if (e.message?.contains("404") == true)
                    "your hub is older than this app. Update Stellar Hub on your PC (dashboard → Check for updates), then tap Share again."
                else explain(e)
                main.post {
                    if (isFinishing) return@post
                    prefs.edit().putBoolean("share_music", false).apply()
                    Toast.makeText(this, "Couldn't share your music: $why", Toast.LENGTH_LONG).show()
                    if (tab == "hub") showTab("hub")
                }
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 7) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) shareMusic(true)
            else { prefs.edit().putBoolean("share_music", false).apply(); toast("Music access is needed to share your song list"); if (tab == "hub") showTab("hub") }
        }
    }

    /** The resident asked for a song: Stellar Disc plays it, but only while the app is on screen. */
    private fun playOnPhone(req: JSONObject) {
        val id = req.optLong("id")
        if (!resumed || !prefs.getBoolean("share_music", false) || id == prefs.getLong("played_id", 0L)) return
        prefs.edit().putLong("played_id", id).apply()
        val title = req.optString("title")
        val artist = req.optString("artist")
        var ok = false
        var note = ""
        if (!discInstalled()) note = "Stellar Disc isn't installed" else {
            val query = if (artist.isNotBlank() && artist != "unknown artist") "$title by $artist" else title
            val intent = Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH).setPackage(discPackage)
                .putExtra(SearchManager.QUERY, query)
            try {
                startActivity(intent)   // opens on top of Hub Connect S: Back comes straight back here
                ok = true
                val who = lastStatus?.optString("name")?.takeIf { it.isNotBlank() && it != "null" } ?: "Your resident"
                toast("$who put on \"$title\" in Stellar Disc")
            } catch (e: Exception) {
                note = e.message ?: "couldn't open Stellar Disc"
            }
        }
        bgTask({ it.post("/api/phone/played", JSONObject().put("id", id).put("ok", ok).put("note", note)) }) { }
    }

    private fun pollStatusThenHub() {
        bgTask({ it.getObject("/api/status") }) { s -> applyStatus(s); if (tab == "hub") showTab("hub") }
    }
}

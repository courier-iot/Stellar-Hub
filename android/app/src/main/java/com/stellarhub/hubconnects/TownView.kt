package com.stellarhub.hubconnects

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.os.SystemClock
import android.view.MotionEvent
import android.view.View
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.abs
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sign

/** Draws the Stellar Hub colony from the pixel art the hub serves (same art as the desktop viewer).
 *  The phone shows a window of the colony that follows the resident. Drag to look around.
 *  When the resident walks into a building, the view can follow it inside: every building has its own room. */
class TownView(context: Context) : View(context) {

    private class Building(val id: String, val x: Int, val y: Int, val doorX: Int, val bitmap: Bitmap, val door: IntArray?)
    private class Spot(val x: Int, val top: Int, val fx: String)
    private class Light(val x: Int, val y: Int, val w: Int, val h: Int, val color: Int, val period: Int)
    private class Room(val id: String, val name: String, val version: String, val w: Int, val h: Int, val bitmap: Bitmap,
                       val feetY: Int, val doorX: Int, val spots: Map<String, Spot>, val actions: Map<String, String>,
                       val idle: List<String>, val lights: List<Light>)
    private class Particle(var x: Float, var y: Float, val vx: Float, val vy: Float, val born: Long, val life: Long,
                           val color: Int, val kind: Int)

    private enum class Phase { OUT_WALK, ENTER, INSIDE, LEAVE, EXIT }

    private var worldW = 384
    private var worldH = 216
    private var background: Bitmap? = null
    private var buildings: List<Building> = emptyList()
    private var frames: List<Bitmap> = emptyList()
    private var twinkle: List<Pair<Int, Int>> = emptyList()
    private var feetY = 192
    private var floats = true
    private var decor: List<Building> = emptyList()
    private var away = false
    private var night = false
    private var emotes: Map<String, Bitmap> = emptyMap()
    private var ship: Bitmap? = null
    private var emote: String? = null
    private var daylight: Double? = null
    private var eventType: String? = null
    private var aliases: Map<String, String> = emptyMap()
    private var station: Bitmap? = null
    private var stationX = 520
    private var stationY = 14
    private var inOrbit = false
    private var palette: Map<Char, Int> = emptyMap()

    private val viewW get() = minOf(worldW, 320)
    private var camX = -1f
    private var dragLastX = 0f
    private var manualUntil = 0L

    // where the resident is and what it's doing
    private var phase = Phase.OUT_WALK
    private var phaseStart = 0L
    private var residentX = -1f          // outside, on the walkway
    private var targetX = -1f
    private var location: String? = null // the building the hub says it's in
    private var destId: String? = null   // the building it's walking to
    private var roomId: String? = null   // the room it's in right now
    private var action: String? = null
    private var ix = -1f                 // inside, along the room's floor
    private var itarget = -1f
    private var activeSpot: String? = null
    private var faceLeft = false
    private var nextWander = 0L
    private var lastFx = 0L
    private val rnd = java.util.Random()
    private val particles = ArrayList<Particle>()

    // the rooms the hub has sent, and which view is on screen
    private val rooms = HashMap<String, Room>()
    private val wanted = HashMap<String, String>()
    private val asked = HashSet<String>()
    private var inside = false
    private var autoEnter = false
    private var fadeStart = 0L

    /** Asks the app to fetch a room from the hub (GET /api/interior/<id>), then hand it to setRoom. */
    var onNeedRoom: ((String) -> Unit)? = null
    /** Called when the view goes inside or back outside, so the app can update its buttons. */
    var onViewChanged: (() -> Unit)? = null
    /** Follow the resident into buildings automatically. */
    var follow = true

    val isInside get() = inside
    val roomName: String? get() = (if (inside) roomId else null)?.let { rooms[it]?.name }
    /** The resident is in a building whose room can be shown. */
    val canGoInside get() = !away && roomId != null && rooms[roomId] != null && (phase == Phase.INSIDE || phase == Phase.LEAVE)

    private val pixelPaint = Paint().apply { isFilterBitmap = false; isAntiAlias = false }
    private val fadePaint = Paint().apply { isFilterBitmap = false; isAntiAlias = false }
    private val fill = Paint().apply { isAntiAlias = false }
    private val textPaint = Paint().apply {
        isAntiAlias = true
        color = Color.parseColor("#EEF1FF")
        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
        textSize = 11f * resources.displayMetrics.scaledDensity
    }

    private fun bake(rows: JSONArray, palette: Map<Char, Int>): Bitmap {
        val h = rows.length()
        val w = rows.getString(0).length
        val pixels = IntArray(w * h)
        for (y in 0 until h) {
            val row = rows.getString(y)
            for (x in 0 until minOf(w, row.length)) {
                val ch = row[x]
                pixels[y * w + x] = if (ch == '.') Color.TRANSPARENT else (palette[ch] ?: Color.MAGENTA)
            }
        }
        return Bitmap.createBitmap(pixels, w, h, Bitmap.Config.ARGB_8888)
    }

    private fun paletteOf(pj: JSONObject): Map<Char, Int> {
        val pal = HashMap<Char, Int>()
        val keys = pj.keys()
        while (keys.hasNext()) {
            val k = keys.next()
            pal[k[0]] = Color.parseColor(pj.getString(k))
        }
        return pal
    }

    fun setWorld(world: JSONObject) {
        worldW = world.getInt("w")
        worldH = world.getInt("h")
        val pal = paletteOf(world.getJSONObject("palette"))
        palette = pal
        background = bake(world.getJSONArray("background"), pal)
        val bs = world.getJSONArray("buildings")
        buildings = (0 until bs.length()).map { i ->
            val b = bs.getJSONObject(i)
            val id = b.optString("id").takeIf { it.isNotBlank() && it != "null" } ?: ""
            val d = b.optJSONArray("door")?.let { a -> IntArray(4) { a.optInt(it) } }
            Building(id, b.getInt("x"), b.getInt("y"), b.getInt("door_x"), bake(b.getJSONArray("sprite"), pal), d)
        }
        night = world.optBoolean("night", false)
        val ej = world.optJSONObject("emotes")
        val em = HashMap<String, Bitmap>()
        if (ej != null) {
            val ek = ej.keys()
            while (ek.hasNext()) { val k = ek.next(); em[k] = bake(ej.getJSONArray(k), pal) }
        }
        emotes = em
        ship = world.optJSONArray("trader_ship")?.let { bake(it, pal) }
        val al = HashMap<String, String>()
        world.optJSONObject("aliases")?.let { aj -> val ak = aj.keys(); while (ak.hasNext()) { val k = ak.next(); al[k] = aj.getString(k) } }
        aliases = al
        val st = world.optJSONObject("station")
        station = st?.optJSONArray("sprite")?.let { bake(it, pal) }
        if (st != null) { stationX = st.optInt("x", 520); stationY = st.optInt("y", 14) }
        val r = world.getJSONObject("resident")
        val fr = r.getJSONArray("frames")
        frames = (0 until fr.length()).map { bake(fr.getJSONArray(it), pal) }
        feetY = r.getInt("feet_y")
        floats = r.getBoolean("floats")
        val dj = world.optJSONArray("decor")
        decor = if (dj == null) emptyList() else (0 until dj.length()).map { i ->
            val d = dj.getJSONObject(i)
            Building(d.getString("name"), d.getInt("x"), d.getInt("y"), 0, bake(d.getJSONArray("sprite"), pal), null)
        }
        away = world.optBoolean("away", false)
        val tw = world.getJSONArray("twinkle")
        twinkle = (0 until tw.length()).map { tw.getJSONArray(it).let { p -> p.getInt(0) to p.getInt(1) } }
        destId?.let { targetX = doorOf(it) }
        requestLayout()
        invalidate()
    }

    /** A room from GET /api/interior/<id>. */
    fun setRoom(j: JSONObject) {
        val pal = paletteOf(j.getJSONObject("palette"))
        val sp = HashMap<String, Spot>()
        j.optJSONObject("spots")?.let { o ->
            val k = o.keys()
            while (k.hasNext()) { val n = k.next(); val s = o.getJSONObject(n); sp[n] = Spot(s.getInt("x"), s.optInt("top", 80), s.optString("fx")) }
        }
        val acts = HashMap<String, String>()
        j.optJSONObject("actions")?.let { o -> val k = o.keys(); while (k.hasNext()) { val n = k.next(); acts[n] = o.getString(n) } }
        val idle = j.optJSONArray("idle")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        val lights = j.optJSONArray("lights")?.let { a ->
            (0 until a.length()).map { i ->
                val l = a.getJSONArray(i)
                Light(l.getInt(0), l.getInt(1), l.getInt(2), l.getInt(3), pal[l.getString(4)[0]] ?: Color.WHITE, maxOf(100, l.getInt(5)))
            }
        } ?: emptyList()
        val id = j.getString("id")
        val room = Room(id, j.optString("name", id), j.optString("version"), j.getInt("w"), j.getInt("h"),
            bake(j.getJSONArray("background"), pal), j.optInt("feet_y", 142), j.optInt("door_x", 13), sp, acts, idle, lights)
        rooms[id] = room
        asked.remove(id)
        if (id == roomId) {
            if (ix < 0) { ix = room.doorX.toFloat() }
            retarget()
            if (autoEnter && follow && !inside && !away) { autoEnter = false; switchView(true) }
            onViewChanged?.invoke()
        }
        invalidate()
    }

    /** The room couldn't be fetched; it will be asked for again next time. */
    fun roomFailed(id: String) { asked.remove(id) }

    private fun needRoom(id: String) {
        val have = rooms[id]
        val want = wanted[id]
        if ((have == null || (want != null && have.version != want)) && asked.add(id)) onNeedRoom?.invoke(id)
    }

    private fun doorOf(id: String): Float {
        val real = aliases[id] ?: id
        return (buildings.firstOrNull { it.id == real }?.doorX ?: worldW / 2).toFloat()
    }

    private fun buildingOf(id: String?): Building? {
        if (id == null) return null
        val real = aliases[id] ?: id
        return buildings.firstOrNull { it.id == real }
    }

    private fun circle(c: Canvas, x: Float, y: Float, r: Float, color: Int) {
        fill.color = color
        c.drawCircle(x, y, r, fill)
    }

    fun setAway(isAway: Boolean) {
        if (isAway && inside) switchView(false)
        away = isAway
    }

    fun setOrbit(orbit: Boolean) {
        inOrbit = orbit
    }

    fun setLife(emoteName: String?, light: Double?, event: String?) {
        emote = emoteName
        daylight = light
        eventType = event
    }

    /** Switch between the colony and the room the resident is in. */
    fun showInside(want: Boolean) {
        if (want && canGoInside) switchView(true) else if (!want) switchView(false)
    }

    private fun switchView(toInside: Boolean) {
        if (inside == toInside) return
        inside = toInside
        fadeStart = SystemClock.uptimeMillis()
        particles.clear()
        if (!toInside) camX = -1f
        onViewChanged?.invoke()
    }

    /** Where the resident is (from /api/status): its building, what it's doing there, and that room's version. */
    fun setPlace(loc: String, prev: String?, lastTurn: Double, act: String?, roomVersion: String?) {
        if (buildings.isEmpty()) return
        if (roomVersion != null) { wanted[loc] = roomVersion; needRoom(loc) }
        val now = SystemClock.uptimeMillis()
        if (location == null) {                       // first look at the colony
            location = loc
            action = act
            destId = loc
            val fresh = lastTurn > 0 && (System.currentTimeMillis() / 1000.0 - lastTurn) < 120
            if (fresh && prev != null && prev != loc) {
                residentX = doorOf(prev)
                targetX = doorOf(loc)
                phase = Phase.EXIT
                phaseStart = now
            } else {
                residentX = doorOf(loc)
                targetX = residentX
                arrive(loc, atSpot = true)
            }
            onViewChanged?.invoke()
            return
        }
        if (loc == location) {
            if (act != action) { action = act; if (phase == Phase.INSIDE) retarget() }
            return
        }
        location = loc
        action = act
        destId = loc
        targetX = doorOf(loc)
        if (phase == Phase.ENTER) {                   // changed its mind at the door: back out
            phase = Phase.EXIT
            phaseStart = now
        } else if (phase == Phase.INSIDE) {           // head for the airlock
            phase = Phase.LEAVE
            phaseStart = now
            val r = rooms[roomId]
            if (r == null || !inside) ix = r?.doorX?.toFloat() ?: ix
            itarget = r?.doorX?.toFloat() ?: ix
        }
    }

    /** The resident is now inside `id`. */
    private fun arrive(id: String, atSpot: Boolean) {
        roomId = id
        phase = Phase.INSIDE
        phaseStart = SystemClock.uptimeMillis()
        val r = rooms[id]
        ix = r?.doorX?.toFloat() ?: -1f
        retarget()
        if (atSpot && itarget >= 0) ix = itarget
        needRoom(id)
        if (follow && !away) {
            if (r != null) switchView(true) else autoEnter = true
        }
        onViewChanged?.invoke()
    }

    private fun retarget() {
        val r = rooms[roomId] ?: return
        val spotName = action?.let { r.actions[it] } ?: r.idle.firstOrNull() ?: r.spots.keys.firstOrNull()
        activeSpot = spotName
        itarget = spotName?.let { r.spots[it]?.x?.toFloat() } ?: (r.w / 2f)
        if (ix < 0) ix = r.doorX.toFloat()
        nextWander = SystemClock.uptimeMillis() + if (action == "sleep") Long.MAX_VALUE / 4 else 25000L + rnd.nextInt(8000)
    }

    private fun wander() {
        val r = rooms[roomId] ?: return
        val choices = r.idle.filter { it != activeSpot && r.spots.containsKey(it) }
        val pick = if (choices.isEmpty()) return else choices[rnd.nextInt(choices.size)]
        activeSpot = pick
        itarget = r.spots[pick]!!.x.toFloat()
        nextWander = SystemClock.uptimeMillis() + 9000L + rnd.nextInt(8000)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (inside) return true
        val scale = width.toFloat() / viewW
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> { dragLastX = event.x; manualUntil = Long.MAX_VALUE }
            MotionEvent.ACTION_MOVE -> {
                camX = (camX - (event.x - dragLastX) / scale).coerceIn(0f, (worldW - viewW).toFloat())
                dragLastX = event.x
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> manualUntil = SystemClock.uptimeMillis() + 6000
        }
        return true
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = MeasureSpec.getSize(widthMeasureSpec)
        setMeasuredDimension(w, w * worldH / viewW)
    }

    // ------------------------------------------------------------------ movement
    private fun step(now: Long) {
        when (phase) {
            Phase.OUT_WALK -> {
                val dx = targetX - residentX
                if (abs(dx) > 0.5f) {
                    residentX += sign(dx) * min(0.9f, abs(dx))
                    faceLeft = dx < 0
                } else if (destId != null && !away) {
                    residentX = targetX
                    phase = Phase.ENTER
                    phaseStart = now
                }
            }
            Phase.ENTER -> if (now - phaseStart > 750) destId?.let { arrive(it, atSpot = false) }
            Phase.INSIDE -> {
                val dx = itarget - ix
                if (ix >= 0 && abs(dx) > 0.5f) {
                    ix += sign(dx) * min(0.7f, abs(dx))
                    faceLeft = dx < 0
                } else if (now > nextWander) {
                    wander()
                }
            }
            Phase.LEAVE -> {
                val dx = itarget - ix
                if (inside && abs(dx) > 0.5f) {
                    ix += sign(dx) * min(0.9f, abs(dx))
                    faceLeft = dx < 0
                } else if (!inside || now - phaseStart > 400) {
                    residentX = doorOf(roomId ?: destId ?: "home")
                    roomId = null
                    phase = Phase.EXIT
                    phaseStart = now
                    if (inside) switchView(false)
                    onViewChanged?.invoke()
                }
            }
            Phase.EXIT -> if (now - phaseStart > 650) { phase = Phase.OUT_WALK; phaseStart = now }
        }
    }

    // ------------------------------------------------------------------ drawing
    private fun drawResident(c: Canvas, x: Float, feet: Int, walking: Boolean, alpha: Int, t: Double) {
        if (frames.isEmpty()) return
        val bob = if (floats) (sin(t / 380) * 2).roundToInt() - 3 else if (walking && ((t / 160).toLong() % 2 == 1L)) -1 else 0
        val fi = when {
            floats -> ((t / 450).toLong() % 2).toInt()
            walking -> ((t / 160).toLong() % 2).toInt()
            else -> 0
        }.coerceAtMost(frames.size - 1)
        val fx = x.roundToInt() - 8f
        val fy = (feet - 16 + bob).toFloat()
        fill.color = Color.argb(115 * alpha / 255, 0, 0, 0)
        c.drawRect(fx + 4, feet - 1f, fx + 12, feet + 1f, fill)
        fadePaint.alpha = alpha
        if (faceLeft) {
            c.save()
            c.scale(-1f, 1f, fx + 8f, 0f)
            c.drawBitmap(frames[fi], fx, fy, fadePaint)
            c.restore()
        } else {
            c.drawBitmap(frames[fi], fx, fy, fadePaint)
        }
        val bubble = emote?.let { emotes[it] }
        if (bubble != null && !walking && alpha == 255) {
            val wob = if (emote == "z") (sin(t / 600) * 1.5).roundToInt() else 0
            c.drawBitmap(bubble, fx + 9, fy - 10 + wob, pixelPaint)
        }
        if (walking && !floats && (t / 160).toLong() % 4 == 0L) {          // little dust puffs
            fill.color = Color.argb(90, 167, 176, 211)
            c.drawRect(fx + (if (faceLeft) 12 else 2), feet - 1f, fx + (if (faceLeft) 14 else 4), feet.toFloat(), fill)
        }
    }

    /** The airlock opening: a dark gap sliding open from the seam. */
    private fun drawDoorGap(c: Canvas, x: Int, y: Int, w: Int, h: Int, open: Float) {
        if (open <= 0f) return
        val gap = ((w - 2) * open).roundToInt().coerceAtLeast(1)
        val gx = x + (w - gap) / 2f
        fill.color = Color.parseColor("#07080F")
        c.drawRect(gx, y + 1f, gx + gap, (y + h).toFloat(), fill)
        fill.color = Color.argb(70, 255, 243, 196)
        c.drawRect(gx, (y + h - 2).toFloat(), gx + gap, (y + h).toFloat(), fill)
    }

    private fun doorOpenness(now: Long, total: Long): Float {
        val p = (now - phaseStart).toFloat()
        return when {
            p < 200 -> p / 200f
            p > total - 200 -> ((total - p) / 200f).coerceAtLeast(0f)
            else -> 1f
        }
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.BLACK)
        val now = SystemClock.uptimeMillis()
        val t = now.toDouble()
        if (background == null) return
        if (residentX >= 0) step(now)
        val room = rooms[roomId]
        if (inside && room != null) drawRoom(canvas, room, now, t) else {
            if (inside) switchView(false)
            drawColony(canvas, now, t)
        }
        if (now - fadeStart < 350) {                 // quick fade when the view switches
            fill.color = Color.argb((255 * (1 - (now - fadeStart) / 350f)).roundToInt().coerceIn(0, 255), 0, 0, 0)
            canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), fill)
        }
        postInvalidateOnAnimation()
    }

    private fun drawRoom(canvas: Canvas, r: Room, now: Long, t: Double) {
        val scale = width.toFloat() / r.w
        canvas.save()
        canvas.scale(scale, scale)
        canvas.drawBitmap(r.bitmap, 0f, 0f, pixelPaint)
        for (l in r.lights) {
            if ((now / l.period) % 2 == 0L) {
                fill.color = l.color
                canvas.drawRect(l.x.toFloat(), l.y.toFloat(), (l.x + l.w).toFloat(), (l.y + l.h).toFloat(), fill)
            }
        }
        if (night) {
            fill.color = Color.argb(30, 5, 6, 20)
            canvas.drawRect(0f, 0f, r.w.toFloat(), r.h.toFloat(), fill)
        }
        val nearDoor = abs(ix - r.doorX) < 9
        val justIn = phase == Phase.INSIDE && now - phaseStart < 600
        if (nearDoor && (justIn || phase == Phase.LEAVE)) drawDoorGap(canvas, 4, 89, 19, 31, 1f)
        val walking = abs(itarget - ix) > 0.5f
        val alpha = if (justIn) ((now - phaseStart) / 600f * 255).roundToInt().coerceIn(40, 255) else 255
        if (ix >= 0 && !away) {
            drawResident(canvas, ix, r.feetY, walking, alpha, t)
            if (!walking) spawnFx(r, now)
        }
        drawParticles(canvas, now)
        canvas.restore()
        val name = r.name
        val pad = 8f * resources.displayMetrics.density
        val tw = textPaint.measureText(name)
        fill.color = Color.argb(170, 5, 6, 13)
        canvas.drawRect(pad / 2, pad / 2, pad * 1.5f + tw, pad / 2 + textPaint.textSize * 1.5f, fill)
        canvas.drawText(name, pad, pad / 2 + textPaint.textSize * 1.12f, textPaint)
    }

    private fun spawnFx(r: Room, now: Long) {
        val s = activeSpot?.let { r.spots[it] } ?: return
        val doing = activeSpot == action?.let { r.actions[it] }
        val every = if (doing) 450L else 1400L
        if (now - lastFx < every) return
        lastFx = now
        val x = s.x + rnd.nextInt(17) - 8f
        val y = s.top + rnd.nextInt(8).toFloat()
        val p = when (if (doing) s.fx else "sparkle") {
            "notes" -> Particle(x, y, (rnd.nextFloat() - 0.5f) * 0.15f, -0.18f, now, 2200, if (rnd.nextBoolean()) Color.parseColor("#5EF2FF") else Color.parseColor("#FF4FD8"), 3)
            "zzz" -> Particle(s.x + 6f, s.top.toFloat(), 0.08f, -0.12f, now, 2600, Color.parseColor("#A7B0D3"), 4)
            "drops" -> Particle(x, s.top - 4f, 0f, 0.35f, now, 900, Color.parseColor("#5EF2FF"), 1)
            "paint" -> Particle(x, y + 4, 0f, -0.04f, now, 1500, intArrayOf(Color.parseColor("#FF4FD8"), Color.parseColor("#FFD86B"), Color.parseColor("#4FE0A5"), Color.parseColor("#A184FF"))[rnd.nextInt(4)], 1)
            "type", "write" -> Particle(x, y + 6, 0f, 0f, now, 500, Color.WHITE, 1)
            else -> Particle(x, y, 0f, -0.05f, now, 1100, Color.parseColor("#FFF3C4"), 2)
        }
        particles.add(p)
        if (particles.size > 40) particles.removeAt(0)
    }

    private fun drawParticles(c: Canvas, now: Long) {
        val it = particles.iterator()
        while (it.hasNext()) {
            val p = it.next()
            val age = now - p.born
            if (age > p.life) { it.remove(); continue }
            p.x += p.vx; p.y += p.vy
            val a = (255 * (1 - age.toFloat() / p.life)).roundToInt().coerceIn(0, 255)
            fill.color = Color.argb(a, Color.red(p.color), Color.green(p.color), Color.blue(p.color))
            val x = p.x.roundToInt().toFloat(); val y = p.y.roundToInt().toFloat()
            when (p.kind) {
                2 -> { c.drawRect(x - 1, y, x + 2, y + 1, fill); c.drawRect(x, y - 1, x + 1, y + 2, fill) }       // twinkle
                3 -> { c.drawRect(x, y, x + 1, y + 4, fill); c.drawRect(x - 2, y + 3, x + 1, y + 5, fill); c.drawRect(x + 1, y, x + 3, y + 1, fill) } // note
                4 -> { c.drawRect(x, y, x + 3, y + 1, fill); c.drawRect(x + 1, y + 1, x + 2, y + 2, fill); c.drawRect(x, y + 2, x + 3, y + 3, fill) } // z
                else -> c.drawRect(x, y, x + 1, y + 1, fill)
            }
        }
    }

    private fun drawColony(canvas: Canvas, now: Long, t: Double) {
        val bg = background ?: return
        val scale = width.toFloat() / viewW
        val showResident = residentX >= 0 && !away && !inOrbit && (phase == Phase.OUT_WALK || phase == Phase.ENTER || phase == Phase.EXIT)
        // camera: follow the resident (or the spaceport while it's away) unless you're dragging
        val focus = when {
            away || inOrbit -> doorOf("spaceport")
            showResident -> residentX
            roomId != null -> doorOf(roomId!!)
            residentX >= 0 -> residentX
            else -> worldW / 2f
        }
        val wantX = (focus - viewW / 2f).coerceIn(0f, (worldW - viewW).toFloat())
        if (camX < 0) camX = wantX
        if (now > manualUntil) camX += (wantX - camX) * 0.08f
        canvas.save()
        canvas.scale(scale, scale)
        canvas.translate(-camX.roundToInt().toFloat(), 0f)
        canvas.drawBitmap(bg, 0f, 0f, pixelPaint)
        val ev = eventType
        daylight?.let { d ->                    // the colony's star crossing the sky by day
            val sx = (20 + d * (worldW - 40)).toFloat()
            val sy = (70 - sin(Math.PI * d) * 52).toFloat()
            circle(canvas, sx, sy, 22f, Color.argb(26, 255, 216, 107))
            circle(canvas, sx, sy, 13f, Color.argb(64, 255, 216, 107))
            circle(canvas, sx, sy, 8f, if (ev == "eclipse") Color.parseColor("#120f2b") else Color.parseColor("#ffe9a8"))
            fill.color = Color.argb(26, 120, 90, 200)
            canvas.drawRect(0f, 0f, worldW.toFloat(), 138f, fill)
        }
        if (ev == "solar_storm") {               // aurora curtains
            for (band in 0 until 3) {
                fill.color = if (band == 1) Color.argb(46, 255, 79, 216) else Color.argb(46, 79, 224, 165)
                var x = 0
                while (x < worldW) {
                    val y = (30 + band * 14 + sin(x / 37.0 + t / 900 + band) * 10).toFloat()
                    val h = (10 + sin(x / 13.0 + t / 500) * 5).toFloat()
                    canvas.drawRect(x.toFloat(), y, x + 2f, y + h, fill)
                    x += 2
                }
            }
        }
        if (ev == "meteor_shower") {             // streaking meteors
            for (i in 0 until 6) {
                val p = ((t / 1400) + i * 0.37) % 1.0
                val mx = ((i * 157) % worldW + p * 120).toFloat()
                val my = (10 + p * 70 + (i * 13) % 30).toFloat()
                fill.color = Color.WHITE
                canvas.drawRect(mx, my, mx + 2, my + 1, fill)
                fill.color = Color.argb(153, 255, 233, 168)
                canvas.drawRect(mx - 6, my - 3, mx, my - 2, fill)
                canvas.drawRect(mx - 3, my - 1, mx, my, fill)
            }
        }

        station?.let { st ->                    // the Orbital Station, drifting slowly
            val sx = stationX + (sin(t / 4000) * 3).roundToInt()
            val sy = stationY + (sin(t / 2600)).roundToInt()
            canvas.drawBitmap(st, sx.toFloat(), sy.toFloat(), pixelPaint)
            val fast = if (inOrbit) 250 else 900
            if ((t / fast).toLong() % 2 == 1L) {
                fill.color = if (inOrbit) Color.parseColor("#ffd86b") else Color.parseColor("#ff5d73")
                canvas.drawRect(sx + 12f, sy.toFloat(), sx + 14f, sy + 1f, fill)
            }
        }

        twinkle.forEachIndexed { i, (x, y) ->
            val p = sin(t / 600 + i * 1.7)
            if (p > 0.6) {
                fill.color = Color.WHITE
                canvas.drawRect(x.toFloat(), y.toFloat(), x + 1f, y + 1f, fill)
                if (p > 0.93) {
                    fill.color = Color.parseColor("#a7b0d3")
                    canvas.drawRect(x - 1f, y.toFloat(), x + 2f, y + 1f, fill)
                    canvas.drawRect(x.toFloat(), y - 1f, x + 1f, y + 2f, fill)
                }
            }
        }
        for (b in buildings) canvas.drawBitmap(b.bitmap, b.x.toFloat(), b.y.toFloat(), pixelPaint)
        // the airlock opens while the resident goes in or comes out
        val doorB = when (phase) { Phase.ENTER -> buildingOf(destId); Phase.EXIT -> buildings.minByOrNull { abs(it.doorX - residentX) }; else -> null }
        val dr = doorB?.door
        if (doorB != null && dr != null) {
            drawDoorGap(canvas, doorB.x + dr[0], doorB.y + dr[1], dr[2], dr[3], doorOpenness(now, if (phase == Phase.ENTER) 750 else 650))
        }
        for (d in decor) canvas.drawBitmap(d.bitmap, d.x.toFloat(), d.y.toFloat(), pixelPaint)

        for (i in 0 until (worldW / 48 + 1)) {
            val a = (0.25 + 0.25 * sin(t / 400 - i)).coerceIn(0.0, 1.0)
            fill.color = Color.argb((a * 255).toInt(), 0x5e, 0xf2, 0xff)
            canvas.drawRect(4f + i * 48, 190f, 7f + i * 48, 191f, fill)
        }

        val sh = ship
        if (ev == "trader" && sh != null) {      // trader ship hovering over the walkway
            val spot = buildings.firstOrNull { it.id == "spaceport" } ?: buildings.firstOrNull { it.id.isEmpty() } ?: buildings.firstOrNull()
            if (spot != null) {
                val tx = spot.doorX - 12f
                val ty = 152f + (sin(t / 500) * 2).roundToInt()
                canvas.drawBitmap(sh, tx, ty, pixelPaint)
            }
        }
        if (night || ev == "eclipse") {
            fill.color = if (ev == "eclipse") Color.argb(89, 5, 6, 20) else Color.argb(46, 5, 6, 20)
            canvas.drawRect(0f, 138f, worldW.toFloat(), worldH.toFloat(), fill)
        }
        if (showResident) {
            val walking = phase == Phase.OUT_WALK && abs(targetX - residentX) > 0.5f
            val p = (now - phaseStart).toFloat()
            val alpha = when (phase) {
                Phase.ENTER -> (255 * (1 - ((p - 200) / 400f))).roundToInt().coerceIn(0, 255)
                Phase.EXIT -> (255 * ((p - 150) / 400f)).roundToInt().coerceIn(0, 255)
                else -> 255
            }
            drawResident(canvas, residentX, feetY, walking, alpha, t)
        } else if (!away && !inOrbit && roomId != null) {     // a marker over the building it's in
            buildingOf(roomId)?.let { b ->
                val mx = b.doorX.toFloat()
                val my = b.y - 6f + (sin(t / 300) * 1.5).roundToInt()
                fill.color = Color.parseColor("#5EF2FF")
                canvas.drawRect(mx - 2, my, mx + 3, my + 1, fill)
                canvas.drawRect(mx - 1, my + 1, mx + 2, my + 2, fill)
                canvas.drawRect(mx, my + 2, mx + 1, my + 3, fill)
            }
        }
        canvas.restore()
    }

    /** The colony (or the room it's in) as a picture, for photo mode. */
    fun snapshot(scale: Int = 4): Bitmap? {
        val r = rooms[roomId]
        if (inside && r != null) {
            val out = Bitmap.createBitmap(r.w * scale, r.h * scale, Bitmap.Config.ARGB_8888)
            val c = Canvas(out)
            c.scale(scale.toFloat(), scale.toFloat())
            c.drawBitmap(r.bitmap, 0f, 0f, pixelPaint)
            if (ix >= 0 && frames.isNotEmpty()) {
                c.drawBitmap(frames[0], ix.roundToInt() - 8f, (r.feetY - 16).toFloat(), pixelPaint)
            }
            return out
        }
        val bg = background ?: return null
        val out = Bitmap.createBitmap(worldW * scale, worldH * scale, Bitmap.Config.ARGB_8888)
        val c = Canvas(out)
        c.scale(scale.toFloat(), scale.toFloat())
        c.drawBitmap(bg, 0f, 0f, pixelPaint)
        station?.let { c.drawBitmap(it, stationX.toFloat(), stationY.toFloat(), pixelPaint) }
        for (b in buildings) c.drawBitmap(b.bitmap, b.x.toFloat(), b.y.toFloat(), pixelPaint)
        for (d in decor) c.drawBitmap(d.bitmap, d.x.toFloat(), d.y.toFloat(), pixelPaint)
        if (residentX >= 0 && frames.isNotEmpty() && !away && !inOrbit) {
            c.drawBitmap(frames[0], residentX.roundToInt() - 8f, (feetY - 16).toFloat(), pixelPaint)
        }
        return out
    }
}

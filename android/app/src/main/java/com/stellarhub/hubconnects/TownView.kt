package com.stellarhub.hubconnects

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
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
 *  The phone shows a window of the colony that follows the resident. Drag to look around. */
class TownView(context: Context) : View(context) {

    private class Building(val id: String, val x: Int, val y: Int, val doorX: Int, val bitmap: Bitmap)

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

    private val viewW get() = minOf(worldW, 320)
    private var camX = -1f
    private var dragLastX = 0f
    private var manualUntil = 0L

    private var residentX = -1f
    private var targetX = -1f
    private var location: String? = null

    private val pixelPaint = Paint().apply { isFilterBitmap = false; isAntiAlias = false }
    private val fill = Paint().apply { isAntiAlias = false }

    private fun bake(rows: JSONArray, palette: Map<Char, Int>): Bitmap {
        val h = rows.length()
        val w = rows.getString(0).length
        val pixels = IntArray(w * h)
        for (y in 0 until h) {
            val row = rows.getString(y)
            for (x in 0 until w) {
                val ch = row[x]
                pixels[y * w + x] = if (ch == '.') Color.TRANSPARENT else (palette[ch] ?: Color.MAGENTA)
            }
        }
        return Bitmap.createBitmap(pixels, w, h, Bitmap.Config.ARGB_8888)
    }

    fun setWorld(world: JSONObject) {
        worldW = world.getInt("w")
        worldH = world.getInt("h")
        val pal = HashMap<Char, Int>()
        val pj = world.getJSONObject("palette")
        val keys = pj.keys()
        while (keys.hasNext()) {
            val k = keys.next()
            pal[k[0]] = Color.parseColor(pj.getString(k))
        }
        background = bake(world.getJSONArray("background"), pal)
        val bs = world.getJSONArray("buildings")
        buildings = (0 until bs.length()).map { i ->
            val b = bs.getJSONObject(i)
            val id = b.optString("id").takeIf { it.isNotBlank() && it != "null" } ?: ""
            Building(id, b.getInt("x"), b.getInt("y"), b.getInt("door_x"), bake(b.getJSONArray("sprite"), pal))
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
            Building(d.getString("name"), d.getInt("x"), d.getInt("y"), 0, bake(d.getJSONArray("sprite"), pal))
        }
        away = world.optBoolean("away", false)
        val tw = world.getJSONArray("twinkle")
        twinkle = (0 until tw.length()).map { tw.getJSONArray(it).let { p -> p.getInt(0) to p.getInt(1) } }
        location?.let { targetX = doorOf(it) }
        requestLayout()
        invalidate()
    }

    private fun doorOf(id: String): Float {
        val real = aliases[id] ?: id
        return (buildings.firstOrNull { it.id == real }?.doorX ?: worldW / 2).toFloat()
    }

    private fun circle(c: Canvas, x: Float, y: Float, r: Float, color: Int) {
        fill.color = color
        c.drawCircle(x, y, r, fill)
    }

    fun setAway(isAway: Boolean) {
        away = isAway
    }

    fun setOrbit(orbit: Boolean) {
        inOrbit = orbit
    }

    /** The whole colony as a picture, for photo mode. */
    fun snapshot(scale: Int = 4): Bitmap? {
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

    fun setLife(emoteName: String?, light: Double?, event: String?) {
        emote = emoteName
        daylight = light
        eventType = event
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
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

    fun setLocation(loc: String, prev: String?, lastTurn: Double) {
        if (buildings.isEmpty() || loc == location) return
        val fresh = lastTurn > 0 && (System.currentTimeMillis() / 1000.0 - lastTurn) < 120
        if (residentX < 0) residentX = doorOf(if (fresh && prev != null) prev else loc)
        location = loc
        targetX = doorOf(loc)
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = MeasureSpec.getSize(widthMeasureSpec)
        setMeasuredDimension(w, w * worldH / viewW)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.BLACK)
        val bg = background ?: return
        val t = SystemClock.uptimeMillis().toDouble()
        val scale = width.toFloat() / viewW
        // camera: follow the resident (or the spaceport while it's away) unless you're dragging
        val focus = when {
            away || inOrbit -> doorOf("spaceport")
            residentX >= 0 -> residentX
            else -> worldW / 2f
        }
        val wantX = (focus - viewW / 2f).coerceIn(0f, (worldW - viewW).toFloat())
        if (camX < 0) camX = wantX
        if (SystemClock.uptimeMillis() > manualUntil) camX += (wantX - camX) * 0.08f
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
        if (residentX >= 0 && frames.isNotEmpty() && !away && !inOrbit) {
            val dx = targetX - residentX
            val walking = abs(dx) > 0.5f
            if (walking) residentX += sign(dx) * min(0.9f, abs(dx))
            val bob = if (floats) (sin(t / 380) * 2).roundToInt() - 3 else 0
            val fi = when {
                floats -> ((t / 450).toLong() % 2).toInt()
                walking -> ((t / 160).toLong() % 2).toInt()
                else -> 0
            }.coerceAtMost(frames.size - 1)
            val fx = residentX.roundToInt() - 8f
            val fy = (feetY - 16 + bob).toFloat()
            fill.color = Color.argb(115, 0, 0, 0)
            canvas.drawRect(fx + 4, feetY - 1f, fx + 12, feetY + 1f, fill)
            if (walking && dx < 0) {
                canvas.save()
                canvas.scale(-1f, 1f, fx + 8f, 0f)
                canvas.drawBitmap(frames[fi], fx, fy, pixelPaint)
                canvas.restore()
            } else {
                canvas.drawBitmap(frames[fi], fx, fy, pixelPaint)
            }
            val bubble = emote?.let { emotes[it] }
            if (bubble != null && !walking) {
                val wob = if (emote == "z") (sin(t / 600) * 1.5).roundToInt() else 0
                canvas.drawBitmap(bubble, fx + 9, fy - 10 + wob, pixelPaint)
            }
        }
        canvas.restore()
        postInvalidateOnAnimation()
    }
}

package com.stellarhub.hubconnects

import android.graphics.Bitmap
import android.graphics.Color
import org.json.JSONArray
import org.json.JSONObject

/** Turns the hub's pixel-art rows (one palette letter per pixel) into crisp, scaled bitmaps. */
object Pixel {
    fun palette(json: JSONObject): Map<Char, Int> {
        val out = HashMap<Char, Int>()
        val keys = json.keys()
        while (keys.hasNext()) {
            val k = keys.next()
            out[k[0]] = Color.parseColor(json.getString(k))
        }
        return out
    }

    fun bitmap(rows: JSONArray, pal: Map<Char, Int>, scale: Int, background: Int = Color.TRANSPARENT): Bitmap {
        val h = rows.length()
        val w = if (h > 0) rows.getString(0).length else 1
        val px = IntArray(w * h)
        for (y in 0 until h) {
            val r = rows.getString(y)
            for (x in 0 until w) {
                val ch = if (x < r.length) r[x] else '.'
                px[y * w + x] = if (ch == '.') background else (pal[ch] ?: background)
            }
        }
        val small = Bitmap.createBitmap(px, maxOf(1, w), maxOf(1, h), Bitmap.Config.ARGB_8888)
        return Bitmap.createScaledBitmap(small, maxOf(1, w * scale), maxOf(1, h * scale), false)
    }
}

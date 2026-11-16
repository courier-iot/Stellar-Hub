package com.stellarhub.hubconnects

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import org.json.JSONArray
import org.json.JSONObject

/** Stellar Disc tells us which songs you play, finish or skip (only if you turned that on in both apps).
 *  The events wait here and go to the hub when the app is open or on the next background check. */
class ListenReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        if (intent.action != "com.stellapp.disc.LISTEN") return
        val p = Notifier.prefs(ctx)
        if (!p.getBoolean("share_listening", false)) return
        if ((p.getString("role", "owner") ?: "owner") != "owner") return     // listening together is the owner's
        val event = intent.getStringExtra("event") ?: return
        if (event !in listOf("play", "complete", "skip")) return
        val title = intent.getStringExtra("title")?.take(120)?.takeIf { it.isNotBlank() } ?: return
        ListenQueue.add(ctx, JSONObject()
            .put("event", event).put("title", title)
            .put("artist", intent.getStringExtra("artist")?.take(80) ?: "")
            .put("duration", intent.getLongExtra("duration", 0))
            .put("ts", intent.getLongExtra("ts", System.currentTimeMillis() / 1000)))
        if (ListenQueue.appVisible) {      // listening together: send it right away
            val pending = goAsync()
            Thread {
                try { ListenQueue.flush(ctx, foreground = true) } finally { pending.finish() }
            }.start()
        }
    }
}

object ListenQueue {
    @Volatile var appVisible = false
    private val lock = Any()

    fun add(ctx: Context, e: JSONObject) = synchronized(lock) {
        val p = Notifier.prefs(ctx)
        val arr = try { JSONArray(p.getString("listen_queue", "[]")) } catch (x: Exception) { JSONArray() }
        arr.put(e)
        val trimmed = if (arr.length() > 500) JSONArray().also { t -> for (i in arr.length() - 500 until arr.length()) t.put(arr.get(i)) } else arr
        p.edit().putString("listen_queue", trimmed.toString()).apply()
    }

    /** Sends waiting events to the hub. Runs on a background thread. */
    fun flush(ctx: Context, foreground: Boolean = false) {
        val p = Notifier.prefs(ctx)
        if (!p.getBoolean("share_listening", false)) return
        if ((p.getString("role", "owner") ?: "owner") != "owner") return     // listening together is the owner's
        val addr = p.getString("address", "") ?: ""
        val code = p.getString("code", "") ?: ""
        if (addr.isBlank() || code.isBlank()) return
        val arr = synchronized(lock) { try { JSONArray(p.getString("listen_queue", "[]")) } catch (x: Exception) { JSONArray() } }
        if (arr.length() == 0) return
        try {
            Api(addr, code, foreground).post("/api/phone/listening", JSONObject().put("events", arr))
            synchronized(lock) {     // drop what was sent; keep anything that arrived meanwhile
                val now = try { JSONArray(p.getString("listen_queue", "[]")) } catch (x: Exception) { JSONArray() }
                val rest = JSONArray()
                for (i in arr.length() until now.length()) rest.put(now.get(i))
                p.edit().putString("listen_queue", rest.toString()).apply()
            }
        } catch (e: Exception) {
            // the hub is offline: try again later
        }
    }
}

package com.stellarhub.hubconnects

import android.app.RemoteInput
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import org.json.JSONObject

/** Handles Approve / Deny / Answer tapped right on a notification. */
class ActionReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Notifier.ACTION) return
        val req = intent.getIntExtra("req", 0)
        val decision = intent.getStringExtra("decision") ?: "noted"
        val notif = intent.getIntExtra("notif", 0)
        val reply = RemoteInput.getResultsFromIntent(intent)?.getCharSequence(Notifier.KEY_REPLY)?.toString() ?: ""
        val ctx = context.applicationContext
        val pending = goAsync()
        Thread {
            try {
                val api = Notifier.api(ctx) ?: throw ApiException("Not paired")
                api.post("/api/requests/$req/reply", JSONObject().put("decision", decision).put("reply", reply))
                val msg = when (decision) {
                    "approved" -> "Approved ✓"
                    "denied" -> "Denied ✓"
                    else -> "Sent ✓"
                }
                Notifier.done(ctx, notif, msg)
            } catch (e: Exception) {
                Notifier.done(ctx, notif, "Couldn't reach Stellar Hub. Open the app to answer.")
            } finally {
                pending.finish()
            }
        }.start()
    }
}

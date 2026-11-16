package com.stellarhub.hubconnects

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.RemoteInput
import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.graphics.drawable.Icon
import android.os.Build
import org.json.JSONObject
import java.util.Calendar

/** Background checks for new requests, questions, letters and colony news. */
object Notifier {
    const val CHANNEL_ASK = "hub_requests"
    const val CHANNEL_NEWS = "hub_news"
    const val ACTION = "com.stellarhub.hubconnects.REPLY_ACTION"
    const val KEY_REPLY = "reply"
    private const val JOB_ID = 4201

    fun prefs(ctx: Context): SharedPreferences = ctx.getSharedPreferences("hub", Context.MODE_PRIVATE)

    fun api(ctx: Context): Api? {
        val p = prefs(ctx)
        val addr = p.getString("address", "") ?: ""
        val code = p.getString("code", "") ?: ""
        return if (addr.isNotBlank() && code.isNotBlank()) Api(addr, code) else null
    }

    fun ensureChannels(ctx: Context) {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CHANNEL_ASK, "Requests & questions", NotificationManager.IMPORTANCE_HIGH)
            .apply { description = "When your resident asks you something or needs approval" })
        nm.createNotificationChannel(NotificationChannel(CHANNEL_NEWS, "Colony news", NotificationManager.IMPORTANCE_DEFAULT)
            .apply { description = "Colony logs, expeditions, plants and finished programs" })
    }

    /** Returns null on success, or a short reason the background check couldn't be scheduled. */
    fun schedule(ctx: Context): String? = try {
        val js = ctx.getSystemService(JobScheduler::class.java)
        val job = JobInfo.Builder(JOB_ID, ComponentName(ctx, NotifyJob::class.java))
            .setPeriodic(15 * 60 * 1000L)
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPersisted(true)
            .build()
        js.schedule(job)
        null
    } catch (e: Exception) {
        "Background notifications couldn't start: ${e.message}"
    }

    fun quietNow(p: SharedPreferences): Boolean {
        val start = p.getInt("quiet_start", 22)
        val end = p.getInt("quiet_end", 7)
        if (start < 0 || end < 0 || start == end) return false
        val h = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        return if (start > end) (h >= start || h < end) else (h in start until end)
    }

    /** Runs on a background thread. Posts any new events as notifications. */
    fun check(ctx: Context) {
        val p = prefs(ctx)
        if (!p.getBoolean("notify", true)) return
        val api = api(ctx) ?: return
        val last = p.getInt("last_event", -1)
        if (last < 0) {   // first check after pairing: start from now, don't flood old history
            val r = api.getObject("/api/events?after=-1")
            p.edit().putInt("last_event", r.getInt("latest")).apply()
            return
        }
        ListenQueue.flush(ctx)
        if (quietNow(p)) return   // try again after quiet hours, nothing is lost
        val r = api.getObject("/api/events?after=$last")
        val events = r.getJSONArray("events")
        var maxId = last
        ensureChannels(ctx)
        for (i in 0 until events.length()) {
            val e = events.getJSONObject(i)
            maxId = maxOf(maxId, e.getInt("id"))
            val kind = e.optString("kind")
            if (kind in listOf("request", "question", "letter") && !e.optBoolean("open", true)) continue
            if (kind == "unlock") continue
            post(ctx, e)
        }
        p.edit().putInt("last_event", maxId).apply()
    }

    private fun mutableFlag() = if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0

    private fun actionIntent(ctx: Context, notifId: Int, req: Int, decision: String, n: Int, mutable: Boolean): PendingIntent {
        val i = Intent(ctx, ActionReceiver::class.java).setAction(ACTION)
            .putExtra("req", req).putExtra("decision", decision).putExtra("notif", notifId)
        val flags = PendingIntent.FLAG_UPDATE_CURRENT or (if (mutable) mutableFlag() else PendingIntent.FLAG_IMMUTABLE)
        return PendingIntent.getBroadcast(ctx, notifId * 10 + n, i, flags)
    }

    fun post(ctx: Context, e: JSONObject) {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        val id = e.getInt("id")
        val kind = e.optString("kind")
        val title = e.optString("title")
        val body = e.optString("body")
        val ref = e.optInt("ref_id", 0)
        val reqKind = e.optString("request_kind")
        val ask = kind in listOf("request", "question", "letter")

        val open = Intent(ctx, MainActivity::class.java).putExtra("tab", if (ask) "inbox" else "colony")
            .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        val openPi = PendingIntent.getActivity(ctx, id, open, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val icon = Icon.createWithResource(ctx, R.drawable.ic_stat_star)

        val b = Notification.Builder(ctx, if (ask) CHANNEL_ASK else CHANNEL_NEWS)
            .setSmallIcon(R.drawable.ic_stat_star)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(Notification.BigTextStyle().bigText(body))
            .setContentIntent(openPi)
            .setAutoCancel(true)

        if (ref > 0 && kind == "request" && reqKind != "letter") {
            val yes = if (reqKind == "run_program") "Run it" else "Approve"
            val no = if (reqKind == "run_program") "Don't run" else "Deny"
            b.addAction(Notification.Action.Builder(icon, yes, actionIntent(ctx, id, ref, "approved", 1, false)).build())
            b.addAction(Notification.Action.Builder(icon, no, actionIntent(ctx, id, ref, "denied", 2, false)).build())
        }
        if (ref > 0 && (kind == "question" || kind == "letter" || (kind == "request" && reqKind != "run_program"))) {
            val label = if (kind == "question") "Answer" else "Reply"
            val decision = when (kind) { "question" -> "noted"; "letter" -> "read"; else -> "noted" }
            val input = RemoteInput.Builder(KEY_REPLY).setLabel(label).build()
            b.addAction(Notification.Action.Builder(icon, label, actionIntent(ctx, id, ref, decision, 3, true))
                .addRemoteInput(input).build())
        }
        nm.notify(id, b.build())
    }

    fun done(ctx: Context, notifId: Int, text: String) {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        ensureChannels(ctx)
        val n = Notification.Builder(ctx, CHANNEL_ASK)
            .setSmallIcon(R.drawable.ic_stat_star)
            .setContentTitle(text)
            .setTimeoutAfter(5000)
            .build()
        nm.notify(notifId, n)
    }
}

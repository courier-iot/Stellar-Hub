package com.stellarhub.hubconnects

import android.app.job.JobParameters
import android.app.job.JobService

/** Android wakes this about every 15 minutes to look for new requests and colony news. */
class NotifyJob : JobService() {
    override fun onStartJob(params: JobParameters): Boolean {
        Thread {
            try {
                Notifier.check(applicationContext)
            } catch (_: Exception) {
                // Hub unreachable (PC off, Tailscale off). Try again next time.
            }
            jobFinished(params, false)
        }.start()
        return true
    }

    override fun onStopJob(params: JobParameters): Boolean = true
}

package com.stellarhub.hubconnects

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class ApiException(message: String) : Exception(message)

/** Talks to Stellar Hub over Tailscale. Every call must run off the main thread. */
class Api(address: String, private val pairCode: String, private val foreground: Boolean = false) {

    val base: String = normalize(address)

    private fun open(path: String, method: String): HttpURLConnection {
        val conn = URL(base + path).openConnection() as HttpURLConnection
        conn.requestMethod = method
        conn.connectTimeout = 8000
        conn.readTimeout = 180000  // chat replies from a local model can take a while
        conn.setRequestProperty("X-Hub-Token", pairCode.trim().uppercase())
        if (foreground) conn.setRequestProperty("X-Hub-App", "open")   // the app is on screen (phone music can play)
        return conn
    }

    private fun read(conn: HttpURLConnection): String {
        try {
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() } ?: ""
            if (code == 401) throw ApiException("Wrong pair code")
            if (code !in 200..299) throw ApiException("Hub answered with error $code")
            return text
        } finally {
            conn.disconnect()
        }
    }

    fun getObject(path: String): JSONObject = JSONObject(read(open(path, "GET")))

    fun getArray(path: String): JSONArray = JSONArray(read(open(path, "GET")))

    fun getBytes(path: String): ByteArray {
        val conn = open(path, "GET")
        try {
            val code = conn.responseCode
            if (code == 401) throw ApiException("Wrong pair code")
            if (code !in 200..299) throw ApiException("Hub answered with error $code")
            return conn.inputStream.use { it.readBytes() }
        } finally {
            conn.disconnect()
        }
    }

    fun post(path: String, body: JSONObject = JSONObject()): JSONObject {
        val conn = open(path, "POST")
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json")
        conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
        return JSONObject(read(conn))
    }

    companion object {
        fun normalize(address: String): String {
            var a = address.trim().trimEnd('/')
            if (!a.startsWith("http://") && !a.startsWith("https://")) a = "http://$a"
            val hostPart = a.substringAfter("://")
            if (!hostPart.contains(":")) a = "$a:8080"
            return a
        }
    }
}

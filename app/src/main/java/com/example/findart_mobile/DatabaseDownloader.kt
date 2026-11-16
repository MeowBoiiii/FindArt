package com.example.findart_mobile

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

class DatabaseDownloader(private val context: Context) {

    // Na razie adres lokalnego serwera na komputerze.
    // Dla emulatora Androida użyjemy adresu 10.0.2.2.
    private val serverUrl = "https://gdc2845k-8001.eun1.devtunnels.ms"

    private val databaseFile = File(context.filesDir, "bwa.db")

    fun updateDatabase(): String {
        val serverInfo = getServerDatabaseInfo()

        val localVersion = if (databaseFile.exists()) {
            calculateSha256(databaseFile)
        } else {
            null
        }

        if (localVersion == serverInfo.first) {
            return "Baza danych jest aktualna."
        }

        downloadDatabase()

        val downloadedVersion = calculateSha256(databaseFile)

        if (downloadedVersion != serverInfo.first) {
            databaseFile.delete()
            throw Exception("Pobrana baza ma nieprawidłową wersję.")
        }

        return "Baza danych została zaktualizowana."
    }

    private fun getServerDatabaseInfo(): Pair<String, Long> {
        val connection = URL("$serverUrl/api/version")
            .openConnection() as HttpURLConnection

        connection.connectTimeout = 5000
        connection.readTimeout = 5000
        connection.requestMethod = "GET"

        try {
            val response = connection.inputStream.bufferedReader().use {
                it.readText()
            }

            val json = JSONObject(response)

            return Pair(
                json.getString("version"),
                json.getLong("size")
            )
        } finally {
            connection.disconnect()
        }
    }

    private fun downloadDatabase() {
        val connection = URL("$serverUrl/api/database")
            .openConnection() as HttpURLConnection

        connection.connectTimeout = 10000
        connection.readTimeout = 30000
        connection.requestMethod = "GET"

        val temporaryFile = File(context.filesDir, "bwa_temp.db")

        try {
            connection.inputStream.use { input ->
                temporaryFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }

            if (temporaryFile.length() == 0L) {
                throw Exception("Pobrany plik bazy jest pusty.")
            }

            if (databaseFile.exists()) {
                databaseFile.delete()
            }

            if (!temporaryFile.renameTo(databaseFile)) {
                throw Exception("Nie udało się zapisać nowej bazy.")
            }
        } finally {
            connection.disconnect()
            if (temporaryFile.exists()) {
                temporaryFile.delete()
            }
        }
    }

    private fun calculateSha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")

        file.inputStream().use { input ->
            val buffer = ByteArray(8192)
            while (true) {
                val bytesRead = input.read(buffer)
                if (bytesRead == -1) break
                digest.update(buffer, 0, bytesRead)
            }
        }

        return digest.digest().joinToString("") {
            "%02x".format(it)
        }
    }
}

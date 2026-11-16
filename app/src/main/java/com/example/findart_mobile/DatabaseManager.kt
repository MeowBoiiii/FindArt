
package com.example.findart_mobile

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import java.io.File

data class Exhibition(
    val id: Int,
    val title: String,
    val eventType: String?,
    val startDate: String?,
    val endDate: String?,
    val description: String?,
    val imageUrl: String?,
    val sourceUrl: String?
)

data class Gallery(
    val name: String,
    val address: String?,
    val city: String?,
    val websiteUrl: String?
)

data class ExhibitionDetails(
    val exhibition: Exhibition,
    val galleries: List<Gallery>
)

class DatabaseManager(context: Context) {

    private val databaseFile = File(context.filesDir, "bwa.db")

    private fun openDatabase(): SQLiteDatabase {
        if (!databaseFile.exists()) {
            throw Exception("Baza danych nie istnieje.")
        }

        return SQLiteDatabase.openDatabase(
            databaseFile.absolutePath,
            null,
            SQLiteDatabase.OPEN_READONLY
        )
    }

    fun getExhibitions(): List<Exhibition> {
        val database = openDatabase()

        return try {
            val exhibitions = mutableListOf<Exhibition>()

            val cursor = database.rawQuery(
                """
                SELECT id, title, event_type, start_date,
                       end_date, description, image_url, source_url
                FROM exhibitions
                ORDER BY start_date
                """.trimIndent(),
                null
            )

            cursor.use {
                while (it.moveToNext()) {
                    exhibitions.add(
                        Exhibition(
                            id = it.getInt(0),
                            title = it.getString(1),
                            eventType = it.getString(2),
                            startDate = it.getString(3),
                            endDate = it.getString(4),
                            description = it.getString(5),
                            imageUrl = it.getString(6),
                            sourceUrl = it.getString(7)
                        )
                    )
                }
            }

            exhibitions
        } finally {
            database.close()
        }
    }

    fun getEventTypes(): List<String> {
        val database = openDatabase()

        return try {
            val types = mutableListOf<String>()

            val cursor = database.rawQuery(
                """
            SELECT DISTINCT event_type
            FROM exhibitions
            WHERE event_type IS NOT NULL
              AND TRIM(event_type) != ''
            ORDER BY event_type COLLATE NOCASE
            """.trimIndent(),
                null
            )

            cursor.use {
                while (it.moveToNext()) {
                    types.add(it.getString(0))
                }
            }

            types
        } finally {
            database.close()
        }
    }

    fun getGalleries(): List<Gallery> {
        val database = openDatabase()

        return try {
            val galleries = mutableListOf<Gallery>()

            val cursor = database.rawQuery(
                """
            SELECT DISTINCT g.name, g.address, g.city, g.website_url
            FROM galleries g
            INNER JOIN exhibition_galleries eg
                ON eg.gallery_id = g.id
            ORDER BY g.name COLLATE NOCASE
            """.trimIndent(),
                null
            )

            cursor.use {
                while (it.moveToNext()) {
                    galleries.add(
                        Gallery(
                            name = it.getString(0),
                            address = it.getString(1),
                            city = it.getString(2),
                            websiteUrl = it.getString(3)
                        )
                    )
                }
            }

            galleries
        } finally {
            database.close()
        }
    }

    fun getExhibitionGalleryNames(): Map<Int, List<String>> {
        val database = openDatabase()

        return try {
            val result = mutableMapOf<Int, MutableList<String>>()

            val cursor = database.rawQuery(
                """
            SELECT eg.exhibition_id, g.name
            FROM exhibition_galleries eg
            INNER JOIN galleries g
                ON g.id = eg.gallery_id
            ORDER BY g.name COLLATE NOCASE
            """.trimIndent(),
                null
            )

            cursor.use {
                while (it.moveToNext()) {
                    val exhibitionId = it.getInt(0)
                    val galleryName = it.getString(1)

                    result.getOrPut(exhibitionId) { mutableListOf() }
                        .add(galleryName)
                }
            }

            result
        } finally {
            database.close()
        }
    }

    fun getExhibitionDetails(exhibitionId: Int): ExhibitionDetails {
        val database = openDatabase()

        return try {
            val exhibitionCursor = database.rawQuery(
                """
                SELECT id, title, event_type, start_date,
                       end_date, description, image_url, source_url
                FROM exhibitions
                WHERE id = ?
                """.trimIndent(),
                arrayOf(exhibitionId.toString())
            )

            val exhibition = exhibitionCursor.use {
                if (!it.moveToFirst()) {
                    throw Exception("Nie znaleziono wystawy.")
                }

                Exhibition(
                    id = it.getInt(0),
                    title = it.getString(1),
                    eventType = it.getString(2),
                    startDate = it.getString(3),
                    endDate = it.getString(4),
                    description = it.getString(5),
                    imageUrl = it.getString(6),
                    sourceUrl = it.getString(7)
                )
            }

            val galleries = mutableListOf<Gallery>()

            val galleryCursor = database.rawQuery(
                """
                SELECT g.name, g.address, g.city, g.website_url
                FROM galleries g
                INNER JOIN exhibition_galleries eg
                    ON eg.gallery_id = g.id
                WHERE eg.exhibition_id = ?
                ORDER BY g.name
                """.trimIndent(),
                arrayOf(exhibitionId.toString())
            )

            galleryCursor.use {
                while (it.moveToNext()) {
                    galleries.add(
                        Gallery(
                            name = it.getString(0),
                            address = it.getString(1),
                            city = it.getString(2),
                            websiteUrl = it.getString(3)
                        )
                    )
                }
            }

            ExhibitionDetails(exhibition, galleries)
        } finally {
            database.close()
        }
    }
}

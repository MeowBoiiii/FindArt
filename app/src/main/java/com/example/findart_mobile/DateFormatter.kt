package com.example.findart_mobile

fun formatDate(value: String?): String? {
    if (value.isNullOrBlank()) return null

    val cleaned = value
        .replace("T", " ")
        .replace(Regex("\\.\\d+"), "")

    return if (cleaned.length >= 16) {
        cleaned.substring(0, 16)
    } else {
        cleaned
    }
}

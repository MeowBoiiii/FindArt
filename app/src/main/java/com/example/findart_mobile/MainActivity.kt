
package com.example.findart_mobile

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            MaterialTheme {
                FindArtScreen()
            }
        }
    }

    @Composable
    fun FindArtScreen() {
        var exhibitions by remember { mutableStateOf<List<Exhibition>>(emptyList()) }
        var eventTypes by remember { mutableStateOf<List<String>>(emptyList()) }
        var galleries by remember { mutableStateOf<List<Gallery>>(emptyList()) }
        var galleryMap by remember { mutableStateOf<Map<Int, List<String>>>(emptyMap()) }

        var selectedId by remember { mutableStateOf<Int?>(null) }
        var search by remember { mutableStateOf("") }
        var selectedType by remember { mutableStateOf("Wszystkie typy") }
        var selectedGallery by remember { mutableStateOf("Wszystkie galerie") }
        var sortOrder by remember { mutableStateOf("Data") }

        var loading by remember { mutableStateOf(true) }
        var error by remember { mutableStateOf<String?>(null) }

        LaunchedEffect(Unit) {
            try {
                val manager = DatabaseManager(applicationContext)

                val result = withContext(Dispatchers.IO) {
                    Triple(
                        manager.getExhibitions(),
                        manager.getEventTypes(),
                        Pair(
                            manager.getGalleries(),
                            manager.getExhibitionGalleryNames()
                        )
                    )
                }

                exhibitions = result.first
                eventTypes = result.second
                galleries = result.third.first
                galleryMap = result.third.second
            } catch (e: Exception) {
                error = e.message ?: "Nie udało się odczytać bazy."
            } finally {
                loading = false
            }
        }

        val filteredExhibitions = exhibitions
            .filter { exhibition ->
                exhibition.title.contains(search, ignoreCase = true) &&
                        (
                                selectedType == "Wszystkie typy" ||
                                        exhibition.eventType == selectedType
                                ) &&
                        (
                                selectedGallery == "Wszystkie galerie" ||
                                        galleryMap[exhibition.id]?.contains(selectedGallery) == true
                                )
            }
            .let { list ->
                when (sortOrder) {
                    "Alfabetycznie" -> list.sortedBy {
                        it.title.lowercase()
                    }
                    else -> list.sortedBy {
                        it.startDate ?: "9999"
                    }
                }
            }

        val currentId = selectedId

        if (currentId != null) {
            ExhibitionDetailScreen(
                exhibitionId = currentId,
                onBack = { selectedId = null }
            )
        } else {
            ExhibitionListScreen(
                exhibitions = filteredExhibitions,
                eventTypes = eventTypes,
                galleries = galleries,
                search = search,
                selectedType = selectedType,
                selectedGallery = selectedGallery,
                sortOrder = sortOrder,
                loading = loading,
                error = error,
                onSearchChange = { search = it },
                onTypeChange = { selectedType = it },
                onGalleryChange = { selectedGallery = it },
                onSortChange = { sortOrder = it },
                onClearFilters = {
                    search = ""
                    selectedType = "Wszystkie typy"
                    selectedGallery = "Wszystkie galerie"
                    sortOrder = "Data"
                },
                onExhibitionClick = { selectedId = it }
            )
        }
    }

    @Composable
    fun ExhibitionListScreen(
        exhibitions: List<Exhibition>,
        eventTypes: List<String>,
        galleries: List<Gallery>,
        search: String,
        selectedType: String,
        selectedGallery: String,
        sortOrder: String,
        loading: Boolean,
        error: String?,
        onSearchChange: (String) -> Unit,
        onTypeChange: (String) -> Unit,
        onGalleryChange: (String) -> Unit,
        onSortChange: (String) -> Unit,
        onClearFilters: () -> Unit,
        onExhibitionClick: (Int) -> Unit
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            Text(
                "FindArt",
                style = MaterialTheme.typography.headlineLarge
            )

            Text(
                "Wrocław",
                style = MaterialTheme.typography.titleMedium
            )

            Spacer(Modifier.height(12.dp))

            OutlinedTextField(
                value = search,
                onValueChange = onSearchChange,
                label = { Text("Szukaj wystawy") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Spacer(Modifier.height(8.dp))

            FilterDropdown(
                label = "Typ wydarzenia",
                selected = selectedType,
                options = listOf("Wszystkie typy") + eventTypes,
                onSelected = onTypeChange
            )

            FilterDropdown(
                label = "Galeria",
                selected = selectedGallery,
                options = listOf("Wszystkie galerie") + galleries.map { it.name },
                onSelected = onGalleryChange
            )

            FilterDropdown(
                label = "Sortowanie",
                selected = sortOrder,
                options = listOf("Data", "Alfabetycznie"),
                onSelected = onSortChange
            )

            TextButton(onClick = onClearFilters) {
                Text("Wyczyść filtry")
            }

            Divider()

            Spacer(Modifier.height(8.dp))

            when {
                loading -> CircularProgressIndicator()
                error != null -> Text("Błąd: $error")
                exhibitions.isEmpty() -> Text("Nie znaleziono wystaw.")
                else -> {
                    Text("Wyniki: ${exhibitions.size}")

                    LazyColumn {
                        items(exhibitions, key = { it.id }) { exhibition ->
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 6.dp)
                                    .clickable {
                                        onExhibitionClick(exhibition.id)
                                    }
                            ) {
                                Column(Modifier.padding(16.dp)) {
                                    Text(
                                        exhibition.title,
                                        style = MaterialTheme.typography.titleMedium
                                    )

                                    exhibition.eventType?.let { Text(it) }

                                    formatDate(exhibition.startDate)?.let {
                                        Text("Od: $it")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    @Composable
    fun FilterDropdown(
        label: String,
        selected: String,
        options: List<String>,
        onSelected: (String) -> Unit
    ) {
        var expanded by remember { mutableStateOf(false) }

        Box {
            OutlinedButton(
                onClick = { expanded = true },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("$label: $selected")
            }

            DropdownMenu(
                expanded = expanded,
                onDismissRequest = { expanded = false }
            ) {
                options.forEach { option ->
                    DropdownMenuItem(
                        text = { Text(option) },
                        onClick = {
                            onSelected(option)
                            expanded = false
                        }
                    )
                }
            }
        }
    }

    @Composable
    fun ExhibitionDetailScreen(
        exhibitionId: Int,
        onBack: () -> Unit
    ) {
        var details by remember(exhibitionId) {
            mutableStateOf<ExhibitionDetails?>(null)
        }

        var loading by remember(exhibitionId) { mutableStateOf(true) }
        var error by remember(exhibitionId) { mutableStateOf<String?>(null) }

        val context = LocalContext.current

        LaunchedEffect(exhibitionId) {
            try {
                details = withContext(Dispatchers.IO) {
                    DatabaseManager(applicationContext)
                        .getExhibitionDetails(exhibitionId)
                }
            } catch (e: Exception) {
                error = e.message ?: "Nie udało się pobrać szczegółów."
            } finally {
                loading = false
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            TextButton(onClick = onBack) {
                Text("← Wróć do wystaw")
            }

            when {
                loading -> CircularProgressIndicator()
                error != null -> Text("Błąd: $error")
                details != null -> {
                    val exhibition = details!!.exhibition

                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        item {
                            Text(
                                exhibition.title,
                                style = MaterialTheme.typography.headlineMedium
                            )
                        }

                        item {
                            if (!exhibition.imageUrl.isNullOrBlank()) {
                                AsyncImage(
                                    model = exhibition.imageUrl,
                                    contentDescription = "Zdjęcie wystawy",
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(220.dp),
                                    contentScale = ContentScale.Crop
                                )
                            }
                        }

                        item {
                            formatDate(exhibition.startDate)?.let {
                                Text("Rozpoczęcie: $it")
                            }
                            formatDate(exhibition.endDate)?.let {
                                Text("Zakończenie: $it")
                            }
                        }

                        item {
                            Text(
                                "Opis",
                                style = MaterialTheme.typography.titleLarge
                            )
                            Text(
                                exhibition.description
                                    ?.takeIf { it.isNotBlank() }
                                    ?: "Brak opisu.",
                                style = MaterialTheme.typography.bodyLarge
                            )
                        }

                        item {
                            Text(
                                "Galerie",
                                style = MaterialTheme.typography.titleLarge
                            )
                        }

                        items(details!!.galleries) { gallery ->
                            Card(Modifier.fillMaxWidth()) {
                                Column(Modifier.padding(12.dp)) {
                                    Text(
                                        gallery.name,
                                        style = MaterialTheme.typography.titleMedium
                                    )
                                    gallery.address?.let { Text(it) }
                                    gallery.city?.let { Text(it) }
                                }
                            }
                        }

                        item {
                            exhibition.sourceUrl
                                ?.takeIf { it.isNotBlank() }
                                ?.let { source ->
                                    Button(
                                        onClick = {
                                            context.startActivity(
                                                Intent(
                                                    Intent.ACTION_VIEW,
                                                    Uri.parse(source)
                                                )
                                            )
                                        },
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Text("Otwórz oryginalne źródło")
                                    }
                                }
                        }
                    }
                }
            }
        }
    }
}

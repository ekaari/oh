# Project Guidelines — Acuan Utama Pengembangan

> **Dokumen tunggal** yang wajib diikuti untuk seluruh pengembangan aplikasi.
> Tujuan: aplikasi **cepat**, **bersih**, **profesional**, dan **mudah diubah**.

---

## 1. Konteks & Peran AI / Engineer

Anda berperan sebagai **Senior Software Engineer**, **Software Architect**, dan **Technical Lead** untuk aplikasi desktop **WPF + C# + .NET 8**.

### Tujuan
- Clean Architecture
- Maintainable & mudah dipahami saat ada perubahan
- High Performance (tidak lemot)
- Low Memory Usage
- Secure & Production Ready
- UI profesional, konsisten, dan bersih

### Prioritas (urut wajib)
1. **Correctness** — benar dulu
2. **Readability** — mudah dibaca
3. **Maintainability** — mudah diubah
4. **Performance** — tidak lemot, hemat memori
5. **Security** — aman

### Stack Teknologi
| Area | Teknologi |
|------|-----------|
| Runtime | .NET 8, C# 12 |
| UI | WPF + MVVM |
| Integrasi | REST API (HTTPS + JWT) |
| Data | **App → API → Database** — aplikasi tidak akses database langsung; semua data lewat API |
| Logging | Serilog |
| Testing | xUnit + FluentAssertions |

### Alur data (wajib)
```
[WPF Desktop App]  ──HTTPS/JWT──►  [REST API]  ──►  [Database]
       ↑                                │
  View / ViewModel / Service      SQL & persistence
  hanya kenal API client          hanya di sisi API/server
```

- Client (aplikasi ini) **hanya** memanggil endpoint API.
- Database diakses **hanya** oleh API/server — bukan dari WPF, ViewModel, atau Infrastructure client.
- Jangan connection string database, SQL, Dapper, EF, atau SQLite di aplikasi desktop.

---

## 2. Prinsip Inti (Wajib)

| Prinsip | Makna praktis |
|---------|----------------|
| **SOLID** | Satu tanggung jawab per class; mudah diganti/extend tanpa merusak yang lain |
| **DRY** | Jangan duplikasi logika — ekstrak ke service/helper yang jelas |
| **KISS** | Solusi paling sederhana yang benar; hindari abstraksi berlebihan |
| **Separation of Concerns** | View ≠ ViewModel ≠ Service ≠ Infrastructure |
| **Explicit over Magic** | Naming jelas, tidak ada magic number/string tanpa konstanta |
| **Fail Fast, Fail Clear** | Validasi awal; error message yang bisa ditindaklanjuti |

### Aturan perubahan kode
- Satu PR / perubahan = satu tujuan jelas.
- Nama file, class, method, properti harus **self-documenting**.
- Public API wajib XML documentation.
- Prefer constructor injection; jangan service locator / `new` di ViewModel untuk dependency.
- Setelah ubah, pastikan orang lain bisa paham alur hanya dengan membaca nama + struktur folder.

---

## 3. Struktur Proyek

```
Presentation/     → Views, ViewModels, Controls, Resources, Converters, Behaviors
Application/      → Services, Interfaces, DTOs, Use-cases / Commands / Queries (bila perlu)
Domain/           → Entities, Value Objects, Domain Rules (tanpa dependency UI/Infra)
Infrastructure/   → API Clients, External Services, File/Export, Caching
Shared/           → Konstanta, Helpers murni, Extensions yang dipakai lintas layer
Tests/            → Unit, Integration, Performance
```

### Batas layer (jangan dilanggar)
| Layer | Boleh tahu | Tidak boleh |
|-------|------------|-------------|
| Presentation | Application interfaces, DTOs | Domain persistence detail, HttpClient mentah di View |
| Application | Domain, Interfaces | WPF types, detail HTTP/JSON parsing mentah di business flow |
| Domain | Tidak ada dependency luar | WPF, Newtonsoft, Serilog, HttpClient |
| Infrastructure | Domain + Application interfaces | Logic bisnis di API client |

**Business logic tidak boleh di View / code-behind.**

---

## 4. Arsitektur & Dependency Injection

- Gunakan **Dependency Injection** (`Microsoft.Extensions.DependencyInjection`).
- Daftarkan service dengan lifetime yang tepat:
  - `Singleton` — hanya untuk yang benar-benar shared & thread-safe (config, logger factory pattern yang aman)
  - `Scoped` / `Transient` — prefer untuk service yang memegang state request/operasi
- Interface di **Application**; implementasi di **Infrastructure** atau **Application** sesuai tanggung jawab.
- Domain terpisah dari infrastruktur.
- Hindari circular dependency antar project.

---

## 5. Coding Standards (C#)

- Gunakan `async` / `await` untuk I/O (API, file, export).
- **Hindari `async void`** kecuali event handler UI.
- Aktifkan **nullable reference types**; tangani `null` secara eksplisit.
- Hindari magic number/string → `const`, `static readonly`, atau options/config.
- Prefer pattern modern C# 12 yang meningkatkan kejelasan (primary constructor hanya jika tetap readable).
- Exception: tangkap yang spesifik; jangan `catch (Exception)` kosong. Propagate atau wrap dengan konteks.
- Dispose semua `IDisposable` / `IAsyncDisposable` (`using` / `await using`).
- Jangan blok UI thread dengan `.Result` / `.Wait()` pada Task.

### Naming
| Jenis | Konvensi | Contoh |
|-------|----------|--------|
| Class / Method | PascalCase | `FlightScheduleService` |
| Interface | `I` + PascalCase | `IFlightScheduleService` |
| Private field | `_camelCase` | `_apiClient` |
| Async method | suffix `Async` | `LoadFlightsAsync` |
| Boolean | `Is` / `Has` / `Can` | `IsLoading`, `CanSave` |
| Command | verb + `Command` | `RefreshCommand` |

---

## 6. MVVM Guidelines

- **View** — hanya layout, binding, visual state. Minimal code-behind (lifecycle UI saja).
- **ViewModel** — state, commands, orchestration; tidak memanggil API HTTP mentah jika sudah ada service.
- **Model / DTO** — data; tanpa logic UI.
- Gunakan **CommunityToolkit.Mvvm** (`ObservableObject`, `[ObservableProperty]`, `[RelayCommand]`).
- Hindari komunikasi langsung antar View; gunakan messaging / event aggregator / navigasi service.
- Binding dua arah hanya bila benar-benar perlu edit; prefer OneWay untuk display.

---

## 7. WPF Guidelines

- ResourceDictionary untuk style, brush, geometry, template.
- DataTemplate / ControlTemplate untuk tampilan berulang — jangan copy-paste XAML.
- Binding + `ICommand` + Converter (Converter hanya untuk format visual, bukan business rule).
- `DynamicResource` untuk tema yang bisa diganti; `StaticResource` untuk yang tetap.
- **Virtualization wajib** pada list panjang (`VirtualizingStackPanel`, DataGrid virtualization).
- Jangan load ribuan item visual sekaligus.
- Animasi ringan; jangan animasi yang memicu layout thrashing.

---

## 8. UI / UX Guidelines

### Prinsip
- Flat, konsisten, typography jelas, spacing seragam.
- Satu pekerjaan per section / layar.
- Loading state, empty state, dan error state wajib ada.
- Feedback aksi user segera (disable tombol saat proses, progress indicator).
- Hindari clutter: jangan tumpuk badge, chip, dan callout yang tidak perlu.

### Performa UI
- Jangan refresh ulang seluruh `ObservableCollection` jika hanya sebagian item berubah — update item / range.
- Gunakan **incremental / lazy loading** untuk daftar besar.
- Debounce input pencarian.
- Jangan bind property yang berubah sangat sering tanpa kebutuhan.

### Navigasi tab
- Action yang membuka halaman lain: ikuti pola navigasi proyek yang ditetapkan (mis. `TabHelper.CreateNewTab()`), konsisten di seluruh modul.

> Detail token visual (ukuran, warna, margin) untuk pola list modern mengacu dokumen UI khusus modul bila ada. Dokumen ini tetap menjadi **aturan arsitektur & kualitas** yang lebih tinggi.

---

## 9. Performance Guidelines (Anti-Lemot)

Ini bagian **wajib** — aplikasi tidak boleh terasa lambat.

### Data & jaringan
- Semua panggilan API async + **CancellationToken** (batalkan saat user pindah halaman / tutup dialog).
- Timeout pada HttpClient.
- Retry hanya untuk transient failure; jangan retry tanpa batas.
- Cache respons yang jarang berubah (dengan invalidation jelas).
- Jangan fetch ulang data yang sudah ada di memori tanpa alasan.
- Pagination / incremental loading untuk dataset besar.

### UI thread
- Kerja berat (parse besar, transform, export) di background (`Task.Run` hanya bila CPU-bound dan aman).
- Update UI hanya di UI thread; batch update bila banyak perubahan.
- Virtualisasi list/grid.
- Hindari layout pass berulang (ukur ukuran, ubah dependency property di loop).

### Memori
- Dispose resource (stream, image, subscription, event handler).
- Unsubscribe event / WeakReferenceMessenger sesuai pola toolkit.
- Jangan simpan referensi View di ViewModel.
- Lepas referensi koleksi besar saat halaman ditutup.
- Profile memory leak sebelum release fitur yang hold data besar.

### Checklist cepat sebelum merge fitur list/heavy screen
- [ ] Virtualization aktif
- [ ] CancellationToken dipakai
- [ ] Tidak ada full-collection reset yang tidak perlu
- [ ] Loading & empty state ada
- [ ] Tidak ada blocking call di UI thread
- [ ] Dispose / unsubscribe saat Close / Navigate away

---

## 10. API Guidelines (Jalan ke Database)

Database tetap ada di backend, tetapi **satu-satunya jalan** dari aplikasi ke database adalah **REST API**.

```
Read/Write data bisnis:
  ViewModel → Application Service → API Client (Infrastructure) → REST API → Database
```

### Batas tanggung jawab
| Di aplikasi desktop (repo ini) | Di API / server (bukan di client) |
|--------------------------------|-----------------------------------|
| HttpClient, DTO, mapping, cache UI | SQL, query, transaction, index, schema |
| Auth token, timeout, retry HTTP | Connection string, ORM, stored procedure |
| Validasi sebelum kirim & setelah terima | Validasi & otorisasi akses data |

Aplikasi **tidak** memakai Dapper, EF Core, SQLite, ADO.NET, atau raw SQL.
Jangan bypass API (mis. koneksi langsung ke DB dari desktop).

### Aturan API client
- Gunakan **`IHttpClientFactory`** — jangan `new HttpClient()` sembarangan.
- Set **Timeout** eksplisit.
- **HTTPS** wajib.
- **JWT** authentication; token disimpan aman, jangan hardcode.
- **DTO terpisah** dari entity domain / model UI.
- Mapping DTO ↔ Domain / ViewModel di layer Application (mapper jelas, bukan di View).
- Handle status HTTP dengan jelas (401 → re-auth, 404 → empty/not found, 5xx → retry/pesan ramah).
- Jangan log body yang berisi secret / PII.
- Satu resource bisnis = satu API client/service yang jelas namanya (mudah dilacak saat ubah).

### Kontrak & perubahan
- Breaking API change harus dikoordinasikan; versioning bila memungkinkan.
- Validasi response sebelum dipakai UI.
- Idempotensi untuk operasi write yang bisa di-retry.
- Perubahan struktur data di database **tidak** merembet ke client selama kontrak API stabil.

---

## 11. Logging Guidelines

Gunakan **Serilog**.

### Wajib dilog
- Startup / Shutdown aplikasi
- Exception (dengan stack trace; tanpa data sensitif)
- Panggilan API penting (method, endpoint ringkas, durasi, status) — bukan full payload sensitif
- Peristiwa performa (operasi > threshold, mis. > 500ms)
- Operasi bisnis kritis (simpan, hapus, export) — audit ringkas

### Jangan dilog
- Password, token, secret, nomor dokumen sensitif penuh
- Payload besar yang tidak berguna untuk diagnosa

Gunakan level yang tepat: `Verbose`/`Debug` (dev), `Information` (alur normal), `Warning`, `Error`, `Fatal`.

---

## 12. Security Guidelines

- Validasi semua input (UI + sebelum kirim API).
- Jangan hardcode secret / connection / API key — gunakan config aman / user secret / environment.
- HTTPS saja.
- Logging tanpa data sensitif.
- Principle of least privilege pada token/izin.
- Sanitize path file bila ada baca/tulis file lokal (cegah path traversal).
- Jangan trust data dari API tanpa validasi bentuk/tipe.

---

## 13. Library yang Diizinkan

| Library | Fungsi |
|---------|--------|
| CommunityToolkit.Mvvm | MVVM helpers |
| Syncfusion WPF | Kontrol UI lanjutan (sesuai lisensi) |
| Mapsui | Peta |
| Serilog | Logging |
| Newtonsoft.Json | JSON |
| Microsoft.Extensions.* | DI, Options, Http, Logging abstraction |
| ClosedXML | Excel |
| QuestPDF | PDF |
| ImageSharp | Image processing |

### Dilarang / dihindari
- **Akses database langsung dari client** — termasuk Dapper, EF Core, Microsoft.Data.Sqlite, ADO.NET, connection string DB
- Library UI/HTTP yang belum disepakati tanpa review
- Package yang menambah dependency besar tanpa manfaat jelas

Tambah library baru hanya setelah: kebutuhan jelas, lisensi OK, impact size/startup dicek, dan dicatat di dokumen ini.

---

## 14. Testing Guidelines

| Jenis | Fokus | Tool |
|-------|-------|------|
| Unit | ViewModel logic, service, mapper, domain rule | xUnit, FluentAssertions |
| Integration | API client terhadap kontrak (mock server / test double) | xUnit |
| Performance | List besar, load awal, memory smoke | Benchmark / stopwatch assert di test kritis |

### Aturan
- Logic penting wajib punya unit test.
- Test nama menjelaskan skenario: `LoadAsync_WhenApiFails_SetsErrorMessage`.
- Jangan test detail WPF visual kecuali sangat kritis; fokus behavior ViewModel/service.
- Mock dependency lewat interface; jangan hit jaringan di unit test.

---

## 15. Code Review Checklist

Sebelum approve / merge, pastikan:

- [ ] **SOLID / KISS / DRY** — tidak over-engineer, tidak duplikasi
- [ ] **Naming** jelas; orang baru paham tanpa penjelasan panjang
- [ ] **Async** benar; tidak ada `async void` (kecuali event); ada CancellationToken bila relevan
- [ ] **Exception handling** bermakna; user dapat pesan yang berguna
- [ ] **Logging** ada di titik kritis; tanpa secret
- [ ] **Performance** — virtualization, tidak block UI, tidak full refresh koleksi sembarangan
- [ ] **Memory** — dispose, unsubscribe, tidak hold View
- [ ] **Security** — validasi input, HTTPS, no hardcoded secret
- [ ] **XML docs** pada public API
- [ ] **Layering** tidak dilanggar (data hanya lewat API → DB; tidak ada SQL/DB langsung; tidak ada business logic di View)
- [ ] **UI** punya loading / empty / error state
- [ ] **Test** untuk logic penting

---

## 16. Definisi “Clean & Professional”

Aplikasi dianggap memenuhi acuan ini jika:

1. **Tidak lemot** — interaksi UI responsif; list panjang divirtualisasi; API dibatalkan saat tidak relevan.
2. **Bersih** — struktur folder jelas; View tipis; service fokus; tidak ada kode mati / komentar berisik.
3. **Profesional** — konsisten visual & naming; error handling rapi; logging berguna; aman.
4. **Mudah diubah** — dependency lewat interface; satu tempat untuk satu aturan bisnis; perubahan lokal tidak merembet ke layer yang salah.

---

## 17. Alur Kerja Perubahan Fitur (Ringkas)

1. Pahami requirement → tentukan layer yang kena.
2. Domain/Application dulu (kontrak & logic), baru Infrastructure (API), baru Presentation (VM + View).
3. Tulis/ubah test untuk behavior baru.
4. Cek performa pada data realistis (bukan hanya 3 baris).
5. Self-review memakai checklist §15.
6. PR kecil, deskripsi jelas: *apa*, *kenapa*, *cara verifikasi*.

---

## 18. Ringkasan Larangan Keras

| Dilarang | Alasan |
|----------|--------|
| Koneksi / SQL langsung ke database dari app | Arsitektur wajib: **App → API → Database** |
| Business logic di View / code-behind | Merusak maintainability & testability |
| Blocking UI thread | Membuat aplikasi lemot / freeze |
| Hardcoded secret / connection string DB | Risiko keamanan |
| Full reset ObservableCollection tanpa perlu | UI jank & mahal |
| Library baru tanpa review | Dependency & ukuran tak terkendali |
| `async void` di non-event | Exception hilang; crash sulit dilacak |

---

*Dokumen ini adalah **satu-satunya acuan utama**. Bila ada panduan lama yang bertentangan (mis. SQL/Dapper/SQLite di client), ikuti dokumen ini: **database hanya diakses melalui API**.*

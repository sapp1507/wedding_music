<script setup>
import QRCode from "qrcode";
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";

import {
  createRsvp,
  createSongRequest,
  csvExportUrl,
  deleteSongRequest,
  fetchAllSongs,
  fetchAnnouncement,
  fetchCsrfToken,
  fetchCurrentUser,
  fetchMoments,
  fetchPublicSongs,
  fetchShareLinks,
  fetchSiteStats,
  fetchWeddingPage,
  loginAdmin,
  logoutAdmin,
  markAnnouncementViewed,
  previewSongLink,
  recordSiteVisit,
  setSongApproval,
  updateSongRequest,
} from "./services/api";

const DEFAULT_MOMENTS = [
  { value: "dinner", label: "Фон на банкете" },
  { value: "dance", label: "Танцы" },
  { value: "slow", label: "Медляк" },
  { value: "wishlist", label: "Просто хочу услышать" },
];

const DEFAULT_PAGE = {
  groom_name: "Алексей",
  bride_name: "Мария",
  wedding_date: "2026-09-04T14:45:00+03:00",
  timezone_name: "Europe/Moscow",
  hero_kicker: "4 сентября 2026",
  invitation_text:
    "В нашей жизни скоро состоится важное событие - наша свадьба. Мы будем рады разделить этот день с вами и провести его в кругу самых близких людей.",
  location_title: "Обновление по месту проведения",
  location_name: 'Парк-отель "Жемчужина"',
  location_address: "г. Владимир, Южное шоссе, 23",
  location_map_url: "https://yandex.ru/maps/-/CTRArMpi",
  footer_title: "Будем рады видеть вас на нашем празднике!",
  footer_text: "Спасибо, что разделите с нами этот важный день.",
  events: [],
  faqs: [],
  info_blocks: [],
};

const form = reactive({
  guest_name: "",
  song_title: "",
  artist: "",
  link: "",
  moment: "",
  comment: "",
});

const rsvpForm = reactive({
  guest_name: "",
  attendance: "yes",
  guests_count: 1,
  phone: "",
  comment: "",
});

const weddingPage = ref(DEFAULT_PAGE);
const activeAnnouncement = ref(null);
const shouldShowAnnouncement = ref(false);
const moments = ref(DEFAULT_MOMENTS);
const publicSongs = ref([]);
const adminSongs = ref([]);
const siteStats = ref(null);
const shareLinks = ref(null);
const qrCodes = reactive({
  dj_url: "",
  request_url: "",
});
const activeTab = ref("info");
const isSubmitting = ref(false);
const isSubmittingRsvp = ref(false);
const isPreviewingLink = ref(false);
const isRefreshingDj = ref(false);
const successMessage = ref("");
const errorMessage = ref("");
const rsvpSuccess = ref("");
const rsvpError = ref("");
const adminError = ref("");
const djError = ref("");
const statsError = ref("");
const shareStatus = ref("");
const confirmDeleteId = ref(null);
const authUser = ref(null);
const loginForm = reactive({
  username: "",
  password: "",
});
const rowActions = reactive({});
const isLoggingIn = ref(false);
const isLoadingStats = ref(false);

const canSubmit = computed(() => {
  return form.guest_name.trim() && (form.song_title.trim() || form.link.trim());
});
const canSubmitRsvp = computed(() => rsvpForm.guest_name.trim() && rsvpForm.attendance);
const isAdminView = computed(() => window.location.pathname.startsWith("/admin-list"));
const isDjView = computed(() => window.location.pathname.startsWith("/dj"));
const isAdmin = computed(() => authUser.value?.is_authenticated && authUser.value?.is_staff);
const coupleName = computed(() => `${weddingPage.value.groom_name} и ${weddingPage.value.bride_name}`);
const weddingDate = computed(() => new Date(weddingPage.value.wedding_date));
const weddingDay = computed(() => {
  return weddingDate.value.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
});
const daysUntilWedding = computed(() => {
  const today = new Date();
  const wedding = new Date(weddingDate.value);
  const diff = wedding.setHours(0, 0, 0, 0) - today.setHours(0, 0, 0, 0);
  return Math.max(Math.ceil(diff / 86400000), 0);
});
const sortedPublicSongs = computed(() => {
  return [...publicSongs.value].sort((left, right) => {
    const leftMoment = left.moment_display || "Любой момент";
    const rightMoment = right.moment_display || "Любой момент";
    if (leftMoment !== rightMoment) {
      return leftMoment.localeCompare(rightMoment, "ru");
    }
    return new Date(left.created_at) - new Date(right.created_at);
  });
});
const djSongGroups = computed(() => {
  return sortedPublicSongs.value.reduce((groups, song) => {
    const label = song.moment_display || "Любой момент";
    if (!groups[label]) {
      groups[label] = [];
    }
    groups[label].push(song);
    return groups;
  }, {});
});

function formatEventDate(value) {
  return new Date(value).toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function cookieValue(name) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

function setCookie(name, value, maxAgeSeconds) {
  document.cookie = `${name}=${encodeURIComponent(value)}; max-age=${maxAgeSeconds}; path=/; samesite=lax`;
}

function getOrCreateVisitorId() {
  const existing = cookieValue("wedding_visitor_id");
  if (existing) {
    return decodeURIComponent(existing);
  }
  const generated =
    window.crypto?.randomUUID?.() ||
    `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
  setCookie("wedding_visitor_id", generated, 60 * 60 * 24 * 365);
  return generated;
}

function announcementCookieName(id) {
  return `wedding_announcement_seen_${id}`;
}

async function recordCurrentVisit() {
  if (isAdminView.value) {
    return;
  }
  try {
    await recordSiteVisit({
      visitor_id: getOrCreateVisitorId(),
      last_path: window.location.pathname,
    });
  } catch (error) {
    // Visitor statistics should not block the guest experience.
  }
}

async function loadAnnouncement() {
  if (isAdminView.value || isDjView.value) {
    return;
  }
  try {
    const response = await fetchAnnouncement();
    activeAnnouncement.value = response.announcement;
    if (!activeAnnouncement.value) {
      shouldShowAnnouncement.value = false;
      return;
    }
    shouldShowAnnouncement.value = !cookieValue(
      announcementCookieName(activeAnnouncement.value.id),
    );
  } catch (error) {
    activeAnnouncement.value = null;
    shouldShowAnnouncement.value = false;
  }
}

async function closeAnnouncement() {
  if (!activeAnnouncement.value) {
    shouldShowAnnouncement.value = false;
    return;
  }
  setCookie(announcementCookieName(activeAnnouncement.value.id), "1", 60 * 60 * 24 * 365);
  shouldShowAnnouncement.value = false;
  try {
    await markAnnouncementViewed(activeAnnouncement.value.id);
  } catch (error) {
    // The cookie is still set so the guest is not bothered again.
  }
}

function resetForm() {
  form.guest_name = "";
  form.song_title = "";
  form.artist = "";
  form.link = "";
  form.moment = "";
  form.comment = "";
}

function resetRsvpForm() {
  rsvpForm.guest_name = "";
  rsvpForm.attendance = "yes";
  rsvpForm.guests_count = 1;
  rsvpForm.phone = "";
  rsvpForm.comment = "";
}

function goToAdminLogin() {
  window.location.href = "/admin-list";
}

async function loadWeddingPage() {
  try {
    weddingPage.value = await fetchWeddingPage();
  } catch (error) {
    weddingPage.value = DEFAULT_PAGE;
  }
}

async function loadPublicSongs() {
  publicSongs.value = await fetchPublicSongs();
}

async function loadMoments() {
  try {
    const loadedMoments = await fetchMoments();
    if (loadedMoments.length) {
      moments.value = loadedMoments;
    }
  } catch (error) {
    moments.value = DEFAULT_MOMENTS;
  }
}

async function refreshDjSongs() {
  djError.value = "";
  isRefreshingDj.value = true;
  try {
    await loadPublicSongs();
  } catch (error) {
    djError.value = error.message;
  } finally {
    isRefreshingDj.value = false;
  }
}

async function detectTrackByLink() {
  errorMessage.value = "";
  const link = form.link.trim();
  if (!link) {
    errorMessage.value = "Укажите ссылку на композицию.";
    return;
  }

  isPreviewingLink.value = true;
  try {
    const preview = await previewSongLink(link);
    if (preview.song_title) {
      form.song_title = preview.song_title;
    }
    if (preview.artist) {
      form.artist = preview.artist;
    }
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isPreviewingLink.value = false;
  }
}

async function submitSong() {
  errorMessage.value = "";
  successMessage.value = "";

  if (!canSubmit.value) {
    errorMessage.value = "Укажите имя и название композиции либо ссылку.";
    return;
  }

  isSubmitting.value = true;
  try {
    const response = await createSongRequest(form);
    successMessage.value = response.message;
    resetForm();
    await loadPublicSongs();
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isSubmitting.value = false;
  }
}

async function submitRsvp() {
  rsvpError.value = "";
  rsvpSuccess.value = "";

  if (!canSubmitRsvp.value) {
    rsvpError.value = "Укажите имя и выберите ответ.";
    return;
  }

  isSubmittingRsvp.value = true;
  try {
    const response = await createRsvp(rsvpForm);
    rsvpSuccess.value = response.message;
    resetRsvpForm();
  } catch (error) {
    rsvpError.value = error.message;
  } finally {
    isSubmittingRsvp.value = false;
  }
}

async function loadAdminSongs() {
  adminError.value = "";
  try {
    await fetchCsrfToken();
    authUser.value = await fetchCurrentUser();
    if (!isAdmin.value) {
      adminSongs.value = [];
      return;
    }
    adminSongs.value = await fetchAllSongs();
  } catch (error) {
    adminError.value = error.message;
  }
}

async function loadShareLinks() {
  adminError.value = "";
  try {
    await fetchCsrfToken();
    authUser.value = await fetchCurrentUser();
    if (!isAdmin.value) {
      shareLinks.value = null;
      return;
    }
    shareLinks.value = await fetchShareLinks();
    qrCodes.dj_url = await QRCode.toDataURL(shareLinks.value.dj_url, {
      margin: 1,
      width: 180,
    });
    qrCodes.request_url = await QRCode.toDataURL(shareLinks.value.request_url, {
      margin: 1,
      width: 180,
    });
  } catch (error) {
    adminError.value = error.message;
  }
}

async function loadSiteStats() {
  statsError.value = "";
  isLoadingStats.value = true;
  try {
    await fetchCsrfToken();
    authUser.value = await fetchCurrentUser();
    if (!isAdmin.value) {
      siteStats.value = null;
      return;
    }
    siteStats.value = await fetchSiteStats();
  } catch (error) {
    statsError.value = error.message;
  } finally {
    isLoadingStats.value = false;
  }
}

async function copyShareLink(key) {
  if (!shareLinks.value?.[key]) {
    return;
  }
  const value = shareLinks.value[key];
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
  } else {
    const input = document.createElement("textarea");
    input.value = value;
    input.setAttribute("readonly", "");
    input.style.position = "fixed";
    input.style.opacity = "0";
    document.body.appendChild(input);
    input.select();
    document.execCommand("copy");
    document.body.removeChild(input);
  }
  shareStatus.value = key === "dj_url" ? "Ссылка для DJ скопирована." : "Ссылка для гостей скопирована.";
  window.setTimeout(() => {
    shareStatus.value = "";
  }, 2500);
}

async function copyShareQr(key) {
  if (!qrCodes[key]) {
    return;
  }
  try {
    if (!navigator.clipboard?.write || !window.ClipboardItem) {
      throw new Error("Clipboard image copy is unavailable.");
    }
    const response = await fetch(qrCodes[key]);
    const blob = await response.blob();
    await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
    shareStatus.value = key === "dj_url" ? "QR для DJ скопирован." : "QR для гостей скопирован.";
  } catch (error) {
    await copyShareLink(key);
    return;
  }
  window.setTimeout(() => {
    shareStatus.value = "";
  }, 2500);
}

function shareLabel(key) {
  return key === "dj_url" ? "DJ" : "гостей";
}

async function submitLogin() {
  adminError.value = "";
  isLoggingIn.value = true;
  try {
    await fetchCsrfToken();
    authUser.value = await loginAdmin(loginForm);
    loginForm.password = "";
    await loadAdminSongs();
    await loadShareLinks();
    if (activeTab.value === "stats") {
      await loadSiteStats();
    }
  } catch (error) {
    adminError.value = error.message;
  } finally {
    isLoggingIn.value = false;
  }
}

async function submitLogout() {
  adminError.value = "";
  try {
    await logoutAdmin();
    authUser.value = null;
    adminSongs.value = [];
    siteStats.value = null;
  } catch (error) {
    adminError.value = error.message;
  }
}

async function toggleApproval(song) {
  const nextValue = !song.approved;
  song.approved = nextValue;
  try {
    await setSongApproval(song.id, nextValue);
    await loadPublicSongs();
  } catch (error) {
    song.approved = !nextValue;
    adminError.value = error.message;
  }
}

async function detectAdminSong(song) {
  adminError.value = "";
  if (!song.link) {
    adminError.value = "У этой заявки нет ссылки.";
    return;
  }

  rowActions[song.id] = "detect";
  try {
    const preview = await previewSongLink(song.link);
    const payload = {};
    if (preview.song_title) {
      payload.song_title = preview.song_title;
    }
    if (preview.artist) {
      payload.artist = preview.artist;
    }
    if (!Object.keys(payload).length) {
      adminError.value = "Не удалось определить название или исполнителя.";
      return;
    }
    const updatedSong = await updateSongRequest(song.id, payload);
    Object.assign(song, updatedSong);
    await loadPublicSongs();
  } catch (error) {
    adminError.value = error.message;
  } finally {
    delete rowActions[song.id];
  }
}

async function deleteAdminSong(song) {
  adminError.value = "";
  rowActions[song.id] = "delete";
  try {
    await deleteSongRequest(song.id);
    adminSongs.value = adminSongs.value.filter((item) => item.id !== song.id);
    confirmDeleteId.value = null;
    await loadPublicSongs();
  } catch (error) {
    adminError.value = error.message;
  } finally {
    delete rowActions[song.id];
  }
}

function requestDeleteConfirmation(song) {
  adminError.value = "";
  confirmDeleteId.value = confirmDeleteId.value === song.id ? null : song.id;
}

function cancelDeleteConfirmation(song) {
  if (confirmDeleteId.value === song.id) {
    confirmDeleteId.value = null;
  }
}

let djRefreshTimer;

onMounted(async () => {
  await loadWeddingPage();
  await recordCurrentVisit();
  await loadAnnouncement();
  loadMoments();
  if (isDjView.value) {
    await refreshDjSongs();
    djRefreshTimer = window.setInterval(refreshDjSongs, 30000);
    return;
  }
  await loadPublicSongs();
  if (isAdminView.value) {
    activeTab.value = "admin";
    await loadAdminSongs();
  }
});

onUnmounted(() => {
  if (djRefreshTimer) {
    window.clearInterval(djRefreshTimer);
  }
});
</script>

<template>
  <main v-if="isDjView" class="dj-shell">
    <header class="dj-header">
      <div>
        <p class="eyebrow">{{ coupleName }} · {{ weddingDay }}</p>
        <h1>Плейлист для DJ</h1>
        <p>Одобренные заявки на свадебный банкет. Список обновляется автоматически.</p>
      </div>
      <button class="secondary-action" :disabled="isRefreshingDj" @click="refreshDjSongs">
        {{ isRefreshingDj ? "Обновляем..." : "Обновить" }}
      </button>
    </header>

    <p v-if="djError" class="status error">{{ djError }}</p>

    <section v-if="publicSongs.length" class="dj-board">
      <div v-for="(songs, moment) in djSongGroups" :key="moment" class="dj-group">
        <h2>{{ moment }}</h2>
        <article v-for="song in songs" :key="song.id" class="dj-track">
          <div>
            <strong>{{ song.song_title || "Трек по ссылке" }}</strong>
            <span>{{ song.artist || "Исполнитель не указан" }}</span>
            <p v-if="song.comment">{{ song.comment }}</p>
            <small>Гость: {{ song.guest_name }}</small>
          </div>
          <a v-if="song.link" :href="song.link" target="_blank" rel="noreferrer">Открыть</a>
        </article>
      </div>
    </section>
    <p v-else class="empty-state">Одобренных заявок пока нет.</p>
  </main>

  <main v-else class="app-shell">
    <div v-if="shouldShowAnnouncement && activeAnnouncement" class="modal-backdrop" role="presentation">
      <section
        class="announcement-modal"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`announcement-title-${activeAnnouncement.id}`"
      >
        <p class="eyebrow">Важная информация</p>
        <h2 :id="`announcement-title-${activeAnnouncement.id}`">{{ activeAnnouncement.title }}</h2>
        <p>{{ activeAnnouncement.body }}</p>
        <button class="primary-action" @click="closeAnnouncement">Понятно</button>
      </section>
    </div>

    <section class="wedding-hero">
      <nav class="top-nav" aria-label="Разделы">
        <strong>{{ weddingPage.groom_name }} + {{ weddingPage.bride_name }}</strong>
        <div class="tabs">
          <button :class="{ active: activeTab === 'info' }" @click="activeTab = 'info'">
            Информация
          </button>
          <button :class="{ active: activeTab === 'list' }" @click="activeTab = 'list'">
            Плейлист
          </button>
          <button
            v-if="isAdminView"
            :class="{ active: activeTab === 'admin' }"
            @click="activeTab = 'admin'; loadAdminSongs()"
          >
            Модерация
          </button>
          <button
            v-if="isAdminView"
            :class="{ active: activeTab === 'links' }"
            @click="activeTab = 'links'; loadShareLinks()"
          >
            QR
          </button>
          <button
            v-if="isAdminView"
            :class="{ active: activeTab === 'stats' }"
            @click="activeTab = 'stats'; loadSiteStats()"
          >
            Статистика
          </button>
          <button v-else @click="goToAdminLogin">
            Войти
          </button>
        </div>
      </nav>

      <div class="hero-content">
        <p class="eyebrow">{{ weddingPage.hero_kicker }}</p>
        <h1>{{ coupleName }}</h1>
        <p class="intro-lead">{{ weddingPage.invitation_text }}</p>
        <div class="hero-actions">
          <a class="primary-action" :href="weddingPage.location_map_url" target="_blank" rel="noreferrer">
            Открыть карту
          </a>
          <button class="secondary-action" @click="activeTab = 'list'">Музыкальные заявки</button>
        </div>
      </div>

      <div class="hero-facts" aria-label="Главная информация">
        <article>
          <span>Дата</span>
          <strong>{{ weddingDay }}</strong>
        </article>
        <article>
          <span>Начало</span>
          <strong>{{ formatEventDate(weddingPage.wedding_date) }}</strong>
        </article>
        <article>
          <span>До свадьбы</span>
          <strong>{{ daysUntilWedding }} дн.</strong>
        </article>
      </div>
    </section>

    <template v-if="activeTab === 'info'">
      <section class="section-band invitation-section">
        <div class="section-heading">
          <p class="eyebrow">Приглашение</p>
          <h2>Дорогие гости</h2>
        </div>
        <p>{{ weddingPage.invitation_text }}</p>
      </section>

      <section class="section-band program-section">
        <div class="section-heading">
          <p class="eyebrow">Расписание</p>
          <h2>Программа свадьбы</h2>
        </div>
        <div class="timeline">
          <article v-for="event in weddingPage.events" :key="event.id" class="timeline-item">
            <time>{{ formatEventDate(event.starts_at) }}</time>
            <div>
              <h3>{{ event.title }}</h3>
              <p v-if="event.description">{{ event.description }}</p>
            </div>
          </article>
        </div>
      </section>

      <section class="location-band">
        <div>
          <p class="eyebrow">{{ weddingPage.location_title }}</p>
          <h2>{{ weddingPage.location_name }}</h2>
          <p>{{ weddingPage.location_address }}</p>
        </div>
        <a class="primary-action" :href="weddingPage.location_map_url" target="_blank" rel="noreferrer">
          Построить маршрут
        </a>
      </section>

      <section v-if="weddingPage.info_blocks.length" class="section-band">
        <div class="section-heading">
          <p class="eyebrow">Важно знать</p>
          <h2>Полезная информация</h2>
        </div>
        <div class="info-grid">
          <article v-for="block in weddingPage.info_blocks" :key="block.id" class="info-card">
            <h3>{{ block.title }}</h3>
            <p>{{ block.body }}</p>
            <a v-if="block.link_url" :href="block.link_url" target="_blank" rel="noreferrer">
              {{ block.link_label || "Открыть ссылку" }}
            </a>
          </article>
        </div>
      </section>

      <section class="forms-grid">
        <form class="rsvp-form" @submit.prevent="submitRsvp">
          <div class="section-heading compact">
            <p class="eyebrow">Анкета гостя</p>
            <h2>Подтвердите присутствие</h2>
          </div>
          <label>
            Ваше имя
            <input v-model.trim="rsvpForm.guest_name" maxlength="120" required />
          </label>
          <label>
            Ответ
            <select v-model="rsvpForm.attendance">
              <option value="yes">Приду</option>
              <option value="maybe">Уточню позже</option>
              <option value="no">Не смогу</option>
            </select>
          </label>
          <label>
            Количество гостей
            <input v-model.number="rsvpForm.guests_count" type="number" min="1" max="10" />
          </label>
          <label>
            Телефон
            <input v-model.trim="rsvpForm.phone" maxlength="40" />
          </label>
          <label class="wide">
            Комментарий или пожелание
            <textarea v-model.trim="rsvpForm.comment" rows="4" />
          </label>
          <p v-if="rsvpSuccess" class="status success">{{ rsvpSuccess }}</p>
          <p v-if="rsvpError" class="status error">{{ rsvpError }}</p>
          <button class="primary-action" :disabled="isSubmittingRsvp || !canSubmitRsvp">
            {{ isSubmittingRsvp ? "Сохраняем..." : "Подтвердить" }}
          </button>
        </form>

        <form class="request-form music-form" @submit.prevent="submitSong">
          <div class="section-heading compact wide">
            <p class="eyebrow">Музыкальные пожелания</p>
            <h2>Предложите композицию для банкета</h2>
          </div>
          <label>
            Ваше имя
            <input v-model.trim="form.guest_name" maxlength="100" required />
          </label>

          <label>
            Название композиции
            <input v-model.trim="form.song_title" maxlength="200" />
          </label>

          <label>
            Исполнитель
            <input v-model.trim="form.artist" maxlength="200" />
          </label>

          <label>
            Ссылка
            <span class="input-with-action">
              <input
                v-model.trim="form.link"
                type="url"
                placeholder="YouTube, Яндекс Музыка, VK, Spotify"
                @blur="form.link && !form.song_title && !isPreviewingLink && detectTrackByLink()"
              />
              <button type="button" class="field-action" :disabled="isPreviewingLink" @click="detectTrackByLink">
                {{ isPreviewingLink ? "Ищем..." : "Определить" }}
              </button>
            </span>
          </label>

          <label>
            Предпочтительный момент
            <select v-model="form.moment">
              <option value="">На усмотрение DJ</option>
              <option v-for="moment in moments" :key="moment.value" :value="moment.value">
                {{ moment.label }}
              </option>
            </select>
          </label>

          <label class="wide">
            Комментарий
            <textarea v-model.trim="form.comment" rows="4" />
          </label>

          <p v-if="successMessage" class="status success">{{ successMessage }}</p>
          <p v-if="errorMessage" class="status error">{{ errorMessage }}</p>

          <button class="primary-action" :disabled="isSubmitting || !canSubmit">
            {{ isSubmitting ? "Отправляем..." : "Отправить заявку" }}
          </button>
        </form>
      </section>

      <section v-if="weddingPage.faqs.length" class="section-band faq-section">
        <div class="section-heading">
          <p class="eyebrow">FAQ</p>
          <h2>Отвечаем на ваши вопросы</h2>
        </div>
        <details v-for="faq in weddingPage.faqs" :key="faq.id">
          <summary>{{ faq.question }}</summary>
          <p>{{ faq.answer }}</p>
        </details>
      </section>

      <section class="footer-band">
        <p class="eyebrow">{{ weddingDay }}</p>
        <h2>{{ weddingPage.footer_title }}</h2>
        <p>{{ weddingPage.footer_text }}</p>
      </section>
    </template>

    <section v-if="activeTab === 'list'" class="song-list">
      <article v-for="song in publicSongs" :key="song.id" class="song-card">
        <div>
          <h2>{{ song.song_title || "Трек по ссылке" }}</h2>
          <p>{{ song.artist || "Исполнитель не указан" }}</p>
        </div>
        <a v-if="song.link" :href="song.link" target="_blank" rel="noreferrer">Открыть</a>
        <span>{{ song.moment_display || "Любой момент" }}</span>
      </article>
      <p v-if="!publicSongs.length" class="empty-state">Одобренных заявок пока нет.</p>
    </section>

    <section v-if="activeTab === 'admin'" class="admin-panel">
      <div class="admin-header">
        <div>
          <h2>Модерация</h2>
          <p v-if="isAdmin">Вы вошли как {{ authUser.username }}</p>
        </div>
        <div class="admin-actions">
          <a v-if="isAdmin" class="secondary-action" :href="csvExportUrl()">CSV</a>
          <button v-if="isAdmin" class="secondary-action muted" @click="submitLogout">Выйти</button>
        </div>
      </div>
      <p v-if="adminError" class="status error">{{ adminError }}</p>
      <p v-if="shareStatus" class="status success">{{ shareStatus }}</p>

      <form v-if="!isAdmin" class="login-form" @submit.prevent="submitLogin">
        <label>
          Логин администратора
          <input v-model.trim="loginForm.username" autocomplete="username" required />
        </label>
        <label>
          Пароль
          <input v-model="loginForm.password" type="password" autocomplete="current-password" required />
        </label>
        <button class="primary-action" :disabled="isLoggingIn">
          {{ isLoggingIn ? "Входим..." : "Войти" }}
        </button>
      </form>

      <template v-else>
        <article
          v-for="song in adminSongs"
          :key="song.id"
          class="admin-row"
          :class="song.approved ? 'is-approved' : 'is-pending'"
        >
          <div>
            <strong>{{ song.song_title || "Трек по ссылке" }}</strong>
            <span>{{ song.guest_name }} · {{ song.artist || "без исполнителя" }}</span>
            <a v-if="song.link" :href="song.link" target="_blank" rel="noreferrer">{{ song.link }}</a>
            <p v-if="song.comment">{{ song.comment }}</p>
          </div>
          <div class="row-actions">
            <button
              v-if="song.link"
              class="muted-row-action"
              :disabled="!!rowActions[song.id]"
              @click="detectAdminSong(song)"
            >
              {{ rowActions[song.id] === "detect" ? "Ищем..." : "Найти по ссылке" }}
            </button>
            <button
              :class="{ approved: song.approved }"
              :disabled="!!rowActions[song.id]"
              @click="toggleApproval(song)"
            >
              {{ song.approved ? "Одобрено" : "Одобрить" }}
            </button>
            <button
              class="danger-row-action"
              :disabled="!!rowActions[song.id]"
              @click="requestDeleteConfirmation(song)"
            >
              Удалить
            </button>
            <div v-if="confirmDeleteId === song.id" class="delete-confirm-popover" role="dialog" aria-modal="false">
              <strong>Удалить безвозвратно?</strong>
              <span>{{ song.song_title || song.link || "Эта заявка" }}</span>
              <div>
                <button
                  class="danger-row-action"
                  :disabled="rowActions[song.id] === 'delete'"
                  @click="deleteAdminSong(song)"
                >
                  {{ rowActions[song.id] === "delete" ? "Удаляем..." : "Да, удалить" }}
                </button>
                <button
                  class="muted-row-action"
                  :disabled="rowActions[song.id] === 'delete'"
                  @click="cancelDeleteConfirmation(song)"
                >
                  Отмена
                </button>
              </div>
            </div>
          </div>
        </article>
        <p v-if="!adminSongs.length" class="empty-state">Заявок пока нет.</p>
      </template>
    </section>

    <section v-if="activeTab === 'links'" class="admin-panel">
      <div class="admin-header">
        <div>
          <h2>QR и ссылки</h2>
          <p v-if="isAdmin">Вы вошли как {{ authUser.username }}</p>
        </div>
        <button v-if="isAdmin" class="secondary-action muted" @click="submitLogout">Выйти</button>
      </div>
      <p v-if="adminError" class="status error">{{ adminError }}</p>
      <p v-if="shareStatus" class="status success">{{ shareStatus }}</p>

      <form v-if="!isAdmin" class="login-form" @submit.prevent="submitLogin">
        <label>
          Логин администратора
          <input v-model.trim="loginForm.username" autocomplete="username" required />
        </label>
        <label>
          Пароль
          <input v-model="loginForm.password" type="password" autocomplete="current-password" required />
        </label>
        <button class="primary-action" :disabled="isLoggingIn">
          {{ isLoggingIn ? "Входим..." : "Войти" }}
        </button>
      </form>

      <section v-else-if="shareLinks" class="share-panel" aria-label="Ссылки для гостей и DJ">
        <article class="share-card">
          <div>
            <h3>DJ</h3>
            <p>Страница с одобренными музыкальными заявками.</p>
            <code>{{ shareLinks.dj_url }}</code>
          </div>
          <button class="qr-button" @click="copyShareQr('dj_url')">
            <img :src="qrCodes.dj_url" alt="QR-код страницы DJ" />
            <span>Копировать QR</span>
          </button>
          <button class="text-copy-action" @click="copyShareLink('dj_url')">
            Копировать ссылку для {{ shareLabel("dj_url") }}
          </button>
        </article>

        <article class="share-card">
          <div>
            <h3>Гости</h3>
            <p>Страница добавления музыкальных заявок{{ shareLinks.has_secret ? " с секретом." : "." }}</p>
            <code>{{ shareLinks.request_url }}</code>
          </div>
          <button class="qr-button" @click="copyShareQr('request_url')">
            <img :src="qrCodes.request_url" alt="QR-код страницы добавления музыкальных заявок" />
            <span>Копировать QR</span>
          </button>
          <button class="text-copy-action" @click="copyShareLink('request_url')">
            Копировать ссылку для {{ shareLabel("request_url") }}
          </button>
        </article>
      </section>
    </section>

    <section v-if="activeTab === 'stats'" class="admin-panel">
      <div class="admin-header">
        <div>
          <h2>Статистика</h2>
          <p v-if="isAdmin">Посещения сайта и просмотры важных сообщений.</p>
        </div>
        <div class="admin-actions">
          <button v-if="isAdmin" class="secondary-action muted" :disabled="isLoadingStats" @click="loadSiteStats">
            {{ isLoadingStats ? "Обновляем..." : "Обновить" }}
          </button>
          <button v-if="isAdmin" class="secondary-action muted" @click="submitLogout">Выйти</button>
        </div>
      </div>
      <p v-if="statsError" class="status error">{{ statsError }}</p>

      <form v-if="!isAdmin" class="login-form" @submit.prevent="submitLogin">
        <label>
          Логин администратора
          <input v-model.trim="loginForm.username" autocomplete="username" required />
        </label>
        <label>
          Пароль
          <input v-model="loginForm.password" type="password" autocomplete="current-password" required />
        </label>
        <button class="primary-action" :disabled="isLoggingIn">
          {{ isLoggingIn ? "Входим..." : "Войти" }}
        </button>
      </form>

      <template v-else-if="siteStats">
        <section class="stats-grid" aria-label="Статистика сайта">
          <article class="stat-card">
            <span>Уникальные посетители</span>
            <strong>{{ siteStats.unique_visitors }}</strong>
          </article>
          <article class="stat-card">
            <span>Всего визитов</span>
            <strong>{{ siteStats.total_visits }}</strong>
          </article>
          <article class="stat-card">
            <span>Просмотров активной модалки</span>
            <strong>{{ siteStats.active_announcement?.view_count || 0 }}</strong>
          </article>
        </section>

        <section class="announcement-stats" aria-label="Статистика модалок">
          <h3>Модалки</h3>
          <article v-for="item in siteStats.announcements" :key="item.id" class="announcement-stat-row">
            <div>
              <strong>{{ item.title }}</strong>
              <span>
                {{ item.is_active ? "активна" : "неактивна" }}
                · {{ item.show_to_guests ? "показывается гостям" : "скрыта" }}
                · {{ item.archived ? "архив" : "не в архиве" }}
              </span>
            </div>
            <strong>{{ item.view_count }}</strong>
          </article>
        </section>
      </template>
    </section>
  </main>
</template>

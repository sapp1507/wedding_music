<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";

import {
  createSongRequest,
  csvExportUrl,
  fetchAllSongs,
  fetchCsrfToken,
  fetchCurrentUser,
  fetchMoments,
  fetchPublicSongs,
  loginAdmin,
  logoutAdmin,
  previewSongLink,
  setSongApproval,
} from "./services/api";

const form = reactive({
  guest_name: "",
  song_title: "",
  artist: "",
  link: "",
  moment: "",
  comment: "",
});

const DEFAULT_MOMENTS = [
  { value: "dinner", label: "Фон на банкете" },
  { value: "dance", label: "Танцы" },
  { value: "slow", label: "Медляк" },
  { value: "wishlist", label: "Просто хочу услышать" },
];

const moments = ref(DEFAULT_MOMENTS);
const publicSongs = ref([]);
const adminSongs = ref([]);
const activeTab = ref("request");
const isSubmitting = ref(false);
const isPreviewingLink = ref(false);
const isRefreshingDj = ref(false);
const successMessage = ref("");
const errorMessage = ref("");
const adminError = ref("");
const djError = ref("");
const authUser = ref(null);
const loginForm = reactive({
  username: "",
  password: "",
});
const isLoggingIn = ref(false);

const canSubmit = computed(() => {
  return form.guest_name.trim() && (form.song_title.trim() || form.link.trim());
});

const isAdminView = computed(() => window.location.pathname.startsWith("/admin-list"));
const isDjView = computed(() => window.location.pathname.startsWith("/dj"));
const isAdmin = computed(() => authUser.value?.is_authenticated && authUser.value?.is_staff);
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

function resetForm() {
  form.guest_name = "";
  form.song_title = "";
  form.artist = "";
  form.link = "";
  form.moment = "";
  form.comment = "";
}

function goToAdminLogin() {
  window.location.href = "/admin-list";
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
    errorMessage.value = "Вставьте ссылку на трек.";
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
    errorMessage.value = "Укажите имя и хотя бы название трека или ссылку.";
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

async function submitLogin() {
  adminError.value = "";
  isLoggingIn.value = true;
  try {
    await fetchCsrfToken();
    authUser.value = await loginAdmin(loginForm);
    loginForm.password = "";
    await loadAdminSongs();
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

let djRefreshTimer;

onMounted(async () => {
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
        <p class="eyebrow">Алексей и Мария · 04.09.2026</p>
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
    <section class="intro-band">
      <div class="intro-copy">
        <p class="eyebrow">4 сентября 2026 · свадебный банкет</p>
        <h1>Плейлист для свадьбы Алексея и Марии</h1>
        <p class="intro-lead">
          Добавьте трек, который хочется услышать на празднике. Мы соберем заявки,
          одобрим их и передадим DJ.
        </p>
        <div class="hero-badges" aria-label="Темы вечера">
          <span>банкет</span>
          <span>танцы</span>
          <span>мото-вайб</span>
        </div>
      </div>
      <nav class="tabs" aria-label="Разделы">
        <button :class="{ active: activeTab === 'request' }" @click="activeTab = 'request'">
          Заявка
        </button>
        <button :class="{ active: activeTab === 'list' }" @click="activeTab = 'list'">
          Список
        </button>
        <button
          v-if="isAdminView"
          :class="{ active: activeTab === 'admin' }"
          @click="activeTab = 'admin'; loadAdminSongs()"
        >
          Модерация
        </button>
        <button v-else @click="goToAdminLogin">
          Войти
        </button>
      </nav>
    </section>

    <section v-if="activeTab === 'request'" class="content-grid">
      <form class="request-form" @submit.prevent="submitSong">
        <label>
          Имя гостя
          <input v-model.trim="form.guest_name" maxlength="100" required />
        </label>

        <label>
          Название трека
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
          Когда включить
          <select v-model="form.moment">
            <option value="">Не важно</option>
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
          {{ isSubmitting ? "Отправляем..." : "Отправить трек" }}
        </button>
      </form>

      <aside class="side-note">
        <h2>Что уже одобрено</h2>
        <div v-if="publicSongs.length" class="compact-list">
          <article v-for="song in publicSongs.slice(0, 5)" :key="song.id">
            <strong>{{ song.song_title || "Трек по ссылке" }}</strong>
            <span>{{ song.artist || song.guest_name }}</span>
          </article>
        </div>
        <p v-else>Пока список пуст.</p>
      </aside>
    </section>

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
        <article v-for="song in adminSongs" :key="song.id" class="admin-row">
          <div>
            <strong>{{ song.song_title || "Трек по ссылке" }}</strong>
            <span>{{ song.guest_name }} · {{ song.artist || "без исполнителя" }}</span>
            <a v-if="song.link" :href="song.link" target="_blank" rel="noreferrer">{{ song.link }}</a>
            <p v-if="song.comment">{{ song.comment }}</p>
          </div>
          <button :class="{ approved: song.approved }" @click="toggleApproval(song)">
            {{ song.approved ? "Одобрено" : "Одобрить" }}
          </button>
        </article>
        <p v-if="!adminSongs.length" class="empty-state">Заявок пока нет.</p>
      </template>
    </section>
  </main>
</template>

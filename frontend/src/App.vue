<script setup>
import QRCode from "qrcode";
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";

import {
  createSongRequest,
  csvExportUrl,
  deleteSongRequest,
  fetchAllSongs,
  fetchCsrfToken,
  fetchCurrentUser,
  fetchMoments,
  fetchPublicSongs,
  fetchShareLinks,
  loginAdmin,
  logoutAdmin,
  previewSongLink,
  setSongApproval,
  updateSongRequest,
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
const shareLinks = ref(null);
const qrCodes = reactive({
  dj_url: "",
  request_url: "",
});
const activeTab = ref("request");
const isSubmitting = ref(false);
const isPreviewingLink = ref(false);
const isRefreshingDj = ref(false);
const successMessage = ref("");
const errorMessage = ref("");
const adminError = ref("");
const djError = ref("");
const shareStatus = ref("");
const confirmDeleteId = ref(null);
const authUser = ref(null);
const loginForm = reactive({
  username: "",
  password: "",
});
const rowActions = reactive({});
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
        <button
          v-if="isAdminView"
          :class="{ active: activeTab === 'links' }"
          @click="activeTab = 'links'; loadShareLinks()"
        >
          QR
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
            <a v-if="song.link" :href="song.link" target="_blank" rel="noreferrer">ссылка на трек</a>
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
            <p>Страница с одобренными треками.</p>
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
            <p>Страница добавления треков{{ shareLinks.has_secret ? " с секретом." : "." }}</p>
            <code>{{ shareLinks.request_url }}</code>
          </div>
          <button class="qr-button" @click="copyShareQr('request_url')">
            <img :src="qrCodes.request_url" alt="QR-код страницы добавления треков" />
            <span>Копировать QR</span>
          </button>
          <button class="text-copy-action" @click="copyShareLink('request_url')">
            Копировать ссылку для {{ shareLabel("request_url") }}
          </button>
        </article>
      </section>
    </section>
  </main>
</template>

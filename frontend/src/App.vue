<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import {
  createSongRequest,
  csvExportUrl,
  fetchAllSongs,
  fetchCsrfToken,
  fetchMoments,
  fetchPublicSongs,
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

const moments = ref([]);
const publicSongs = ref([]);
const adminSongs = ref([]);
const activeTab = ref("request");
const isSubmitting = ref(false);
const successMessage = ref("");
const errorMessage = ref("");
const adminError = ref("");

const canSubmit = computed(() => {
  return form.guest_name.trim() && (form.song_title.trim() || form.link.trim());
});

const isAdminView = computed(() => window.location.pathname.startsWith("/admin-list"));

function resetForm() {
  form.guest_name = "";
  form.song_title = "";
  form.artist = "";
  form.link = "";
  form.moment = "";
  form.comment = "";
}

async function loadPublicSongs() {
  publicSongs.value = await fetchPublicSongs();
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
    adminSongs.value = await fetchAllSongs();
  } catch (error) {
    adminError.value = "Войдите в Django admin, чтобы модерировать заявки.";
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

onMounted(async () => {
  moments.value = await fetchMoments();
  await loadPublicSongs();
  if (isAdminView.value) {
    activeTab.value = "admin";
    await loadAdminSongs();
  }
});
</script>

<template>
  <main class="app-shell">
    <section class="intro-band">
      <div>
        <p class="eyebrow">Wedding music</p>
        <h1>Музыкальные заявки гостей</h1>
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
          <input v-model.trim="form.link" type="url" placeholder="YouTube, Яндекс Музыка, VK, Spotify" />
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
        <h2>Модерация</h2>
        <a class="secondary-action" :href="csvExportUrl()">CSV</a>
      </div>
      <p v-if="adminError" class="status error">{{ adminError }}</p>
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
    </section>
  </main>
</template>

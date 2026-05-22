<script setup>
defineProps({
  size: { type: Number, default: 40 }
})
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" fill="none">
    <defs>
      <linearGradient id="meridian-bg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#1e1b4b"/>
        <stop offset="100%" stop-color="#5b21b6"/>
      </linearGradient>
      <linearGradient id="meridian-line" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#c4b5fd"/>
        <stop offset="100%" stop-color="#818cf8"/>
      </linearGradient>
    </defs>

    <!-- Background rounded square -->
    <rect width="40" height="40" rx="9" fill="url(#meridian-bg)"/>

    <!-- Globe outline -->
    <circle cx="20" cy="20" r="11" stroke="url(#meridian-line)" stroke-width="1.4" opacity="0.9"/>

    <!-- Left meridian arc -->
    <path d="M20 9 C12.5 13.5 12.5 26.5 20 31" stroke="url(#meridian-line)" stroke-width="1.4" opacity="0.6"/>

    <!-- Right meridian arc -->
    <path d="M20 9 C27.5 13.5 27.5 26.5 20 31" stroke="url(#meridian-line)" stroke-width="1.4" opacity="0.6"/>

    <!-- Equator line -->
    <line x1="9" y1="20" x2="31" y2="20" stroke="url(#meridian-line)" stroke-width="1.4" opacity="0.6"/>

    <!-- Apex zenith dot — the meridian point -->
    <circle cx="20" cy="9" r="2.5" fill="white"/>

    <!-- Soft glow behind apex -->
    <circle cx="20" cy="9" r="4.5" fill="white" opacity="0.12"/>
  </svg>
</template>

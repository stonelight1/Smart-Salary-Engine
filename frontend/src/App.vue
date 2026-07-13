<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'

const route = useRoute()
const showHeader = computed(() => route.name !== 'Login')
</script>

<template>
  <AppHeader v-if="showHeader" />
  <RouterView />
</template>

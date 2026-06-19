<template>
  <div class="list">
    <DebtCard v-for="(d, i) in pastDebts" :key="i" :debt="d" />
  </div>
  
</template>

<script setup>
import { computed } from 'vue'
import DebtCard from '../components/DebtCard.vue'
import debts from '../data/current_debt.json'

const parsePeriodYears = s => {
  const m = String(s || '').trim().match(/^(\d+(?:\.\d+)?)([ymd])$/i)
  if (!m) return Infinity
  const n = parseFloat(m[1])
  const u = m[2].toLowerCase()
  if (u === 'y') return n
  if (u === 'm') return n / 12
  if (u === 'd') return n / 365
  return Infinity
}

const endMs = d => {
  const start = new Date(d.begin_date)
  const years = parsePeriodYears(d.period)
  const ms = (isNaN(start.getTime()) ? Date.now() : start.getTime()) + years * 365 * 24 * 3600 * 1000
  return ms
}

const isExpired = d => Date.now() > endMs(d)
const pastDebts = computed(() => (debts || []).filter(isExpired))
</script>

<style scoped>
.list {
  display: grid;
  grid-template-columns: 1fr;
  justify-content: center;
  justify-items: center;
  gap: 20px;
  padding: 24px;
}
@media (max-width: 640px) {
  .list { gap: 16px; padding: 16px; }
}
</style>

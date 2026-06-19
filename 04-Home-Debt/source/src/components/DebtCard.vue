<template>
  <div class="card">
    <div class="card-header">
      <div class="title">第{{ debt.issue }}期家债</div>
      <div class="period">{{ debt.period }}</div>
    </div>
    <div class="card-body">
      <div class="stat">
        <div class="label">金额</div>
        <div class="value">{{ formatCurrency(debt.money) }}</div>
      </div>
      <div class="stat">
        <div class="label">利率</div>
        <div class="value">{{ debt.lending_rate }}</div>
      </div>
      <div class="stat">
        <div class="label">开始日期</div>
        <div class="value">{{ debt.begin_date }}</div>
      </div>
    </div>
    <div class="owners">
      <div class="owners-title">出资人</div>
      <ul>
        <li v-for="(o, idx) in ownersWithTotals" :key="idx">
          <span class="owner-name">{{ o.name }}</span>
          <span class="owner-money">{{ formatCurrency(o.money) }}</span>
          <span class="owner-total">{{ formatCurrency(o.current) }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const { debt } = defineProps({
  debt: { type: Object, required: true }
})

const parseRate = r => {
  const v = parseFloat(String(r).replace('%', ''))
  if (Number.isNaN(v)) return 0
  return v / 100
}

const yearsFrom = d => {
  const t = new Date(d)
  const ms = Date.now() - (isNaN(t.getTime()) ? Date.now() : t.getTime())
  const y = ms / (365 * 24 * 3600 * 1000)
  return y < 0 ? 0 : y
}

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

const rate = computed(() => parseRate(debt.lending_rate))
const years = computed(() => yearsFrom(debt.begin_date))
const periodYears = computed(() => parsePeriodYears(debt.period))
const elapsed = computed(() => Math.min(years.value, periodYears.value))
const ownersWithTotals = computed(() =>
  (debt.owner || []).map(o => ({
    ...o,
    current: Number(o.money) * (1 + rate.value * elapsed.value)
  }))
)

const formatCurrency = n => new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)
</script>

<style scoped>
.card {
  width: 100%;
  max-width: 680px;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  overflow: hidden;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #f7f9fc;
  border-bottom: 1px solid #eee;
}
.title {
  font-size: 18px;
  font-weight: 600;
}
.period {
  font-size: 14px;
  color: #666;
}
.card-body {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 16px 20px;
}
.stat .label {
  font-size: 12px;
  color: #777;
}
.stat .value {
  margin-top: 6px;
  font-size: 16px;
  font-weight: 600;
}
.owners {
  padding: 12px 20px 16px;
  border-top: 1px dashed #eee;
}
.owners-title {
  font-size: 14px;
  color: #555;
  margin-bottom: 8px;
}
.owners ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.owners li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 12px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f3f3f3;
}
.owners li:last-child {
  border-bottom: none;
}
.owner-name {
  color: #333;
}
.owner-money {
  color: #666;
}
.owner-total {
  font-weight: 600;
  color: #1677ff;
}

@media (max-width: 640px) {
  .card { border-radius: 8px; }
  .card-body { grid-template-columns: 1fr; }
  .owners li { grid-template-columns: 1fr; }
  .owner-money, .owner-total { justify-self: end; }
}
</style>

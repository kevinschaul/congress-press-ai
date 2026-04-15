---
title: AI Mentions Explorer
---

# AI Mentions in Congressional Press Releases

Press releases from members of Congress mentioning **AI**, **artificial intelligence**, or **data center**. Data via [congress-press](https://thescoop.org/congress-press/). Also available as an [RSS feed](https://kschaul.com/congress-press-ai/feed.xml)

```js
const rawText = await FileAttachment("data/clean/ai-mentions.jsonl").text()
const raw = rawText.trim().split("\n").map(d => JSON.parse(d))
```

```js
import * as Plot from "npm:@observablehq/plot"
import * as d3 from "npm:d3"
```

```js
const PARTY_COLOR = {Democrat: "#1366b3", Republican: "#be2c25", Independent: "#228b22"}
const PARTY_COLOR_LIGHT = {Democrat: "#c8dff2", Republican: "#f2c8c6", Independent: "#c3e0c3"}
const PARTY_ABBREV = {Democrat: "D", Republican: "R", Independent: "I"}

const data = raw.map(d => {
  const abbrev = PARTY_ABBREV[d.party] ?? "?"
  const memberLabel = d.member
    ? `${d.member} (${abbrev}${d.state ? "-" + d.state : ""})`
    : "—"
  return {
    ...d,
    date: new Date(d.date + "T12:00:00"),
    keywordList: d.keywords_found.join(", "),
    snippet: d.snippets?.[0]?.slice(0, 400) ?? "",
    memberLabel,
  }
}).sort((a, b) => b.date - a.date)
```

```js
const months = [...new Set(raw.map(d => d.month))].sort()
const selectedMonth = view(Inputs.select(["All", ...months], {label: "Month"}))
```

```js
const filtered = selectedMonth === "All" ? data : data.filter(d => d.month === selectedMonth)
```

## By party, by day

```js
const partyByDay = d3.flatRollup(
  filtered.filter(d => d.party === "Democrat" || d.party === "Republican"),
  v => v.length,
  d => d3.timeFormat("%Y-%m-%d")(d.date),
  d => d.party
)
.map(([day, party, count]) => ({
  date: new Date(day + "T12:00:00"),
  party,
  count,
}))
.sort((a, b) => a.date - b.date)
```

```js
const rolling7 = ["Democrat", "Republican"].flatMap(party => {
  const pts = partyByDay.filter(d => d.party === party).sort((a, b) => a.date - b.date)
  return pts.map((d, i) => {
    const slice = pts.slice(Math.max(0, i - 6), i + 1)
    return {...d, avg: d3.mean(slice, s => s.count)}
  })
})
```

```js
Plot.plot({
  subtitle: "Line shows 7-day rolling average",
  marks: [
    Plot.gridY({stroke: "#eee", strokeWidth: 1, strokeOpacity: 1, shapeRendering: "crispEdges"}),
    Plot.rectY(partyByDay, {
      x: "date",
      y: "count",
      fy: "party",
      interval: "day",
      fill: d => PARTY_COLOR_LIGHT[d.party] ?? "#ccc",
      tip: true,
    }),
    Plot.lineY(rolling7, {
      x: "date",
      y: "avg",
      fy: "party",
      stroke: "party",
      strokeWidth: 2,
    }),
    Plot.ruleY([0]),
    Plot.text(["Democrat", "Republican"], {
      fy: d => d,
      text: d => d + "s",
      frameAnchor: "top-left",
      dx: 4,
      dy: 26,
      fontSize: 15,
      fontWeight: "bold",
      fill: d => PARTY_COLOR[d],
    }),
  ],
  color: {
    domain: ["Democrat", "Republican"],
    range: [PARTY_COLOR.Democrat, PARTY_COLOR.Republican],
  },
  x: {label: null},
  y: {label: "Count"},
  fy: {label: null, axis: null},
  marginTop: 30,
  width,
  marginLeft: 40,
  marginBottom: 50,
})
```

## Browse mentions

```js
const esc = s => (s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
const highlight = s => esc(s).replace(/(\bAI\b|artificial intelligence|data center)/gi, "<mark>$1</mark>")
```

```js
const selected = view(Inputs.table(filtered, {
  columns: ["date", "memberLabel", "snippet", "url"],
  width: {snippet: 400},
  header: {
    date: "Date",
    memberLabel: "Member",
    snippet: "Context",
    url: "",
  },
  format: {
    date: d => d.toLocaleDateString("en-US"),
    memberLabel: d => {
      const party = d.match(/\(([DRI])/)?.[1]
      const color = party === "D" ? PARTY_COLOR.Democrat : party === "R" ? PARTY_COLOR.Republican : "#333"
      return html`<span style="color:${color};font-weight:bold">${d}</span>`
    },
    snippet: d => {
      const s = d ?? ""
      const el = html`<span style="color:#555;font-size:0.85em;white-space:normal;display:block"></span>`
      el.innerHTML = highlight(s.length > 300 ? s.slice(0, 300) + "…" : s)
      return el
    },
    url: d => html`<a href="${d}" target="_blank" style="text-decoration:none">Original ↗</a>`,
  },
  sort: "date",
  reverse: true,
  rows: 20,
  multiple: false,
}))
```

```js
{
  if (!selected) {
    display(html`<p style="color:#999;font-style:italic;margin-top:0.5rem">Click a row to view the full press release.</p>`)
  } else {
    const fullText = selected.text || selected.snippets?.join("\n\n…\n\n") || ""

    const el = html`<div style="margin-top:1.5rem;padding:1.5rem;border:1px solid #e0e0e0;border-radius:8px;background:#fafafa">
      <h3 style="margin-top:0"></h3>
      <p style="color:#666;margin:0.25rem 0 1rem"></p>
      <div style="font-size:0.9em;line-height:1.7;white-space:pre-wrap;max-height:500px;overflow-y:auto;border-top:1px solid #e0e0e0;padding-top:1rem"></div>
    </div>`

    const link = document.createElement("a")
    link.href = selected.url
    link.target = "_blank"
    link.textContent = selected.title
    el.querySelector("h3").appendChild(link)

    el.querySelector("p").textContent = `${selected.memberLabel} · ${selected.date.toLocaleDateString("en-US", {year: "numeric", month: "long", day: "numeric"})}`
    el.querySelector("div").innerHTML = highlight(fullText)

    display(el)
  }
}
```

## Top members

```js
const memberData = d3.rollups(filtered, v => ({
  count: v.length,
  party: v[0].party,
  state: v[0].state,
}), d => d.member)
  .map(([member, {count, party, state}]) => {
    const abbrev = PARTY_ABBREV[party] ?? "?"
    const label = `${member} (${abbrev}${state ? "-" + state : ""})`
    return {member, label, count, party, state}
  })
  .sort((a, b) => d3.descending(a.count, b.count))
  .slice(0, 25)
```

```js
Plot.plot({
  marks: [
    Plot.barX(memberData, {
      x: "count",
      y: "label",
      fill: d => PARTY_COLOR[d.party] ?? "#999",
      tip: true,
      sort: {y: "-x"},
    }),
    Plot.ruleX([0]),
  ],
  y: {label: null},
  x: {label: "Mentions"},
  width,
  marginLeft: 220,
  height: 550,
})
```

## Keywords

```js
const kwMap = new Map()
for (const d of filtered) {
  for (const kw of d.keywords_found) {
    kwMap.set(kw, (kwMap.get(kw) || 0) + 1)
  }
}
const kwData = [...kwMap.entries()]
  .map(([keyword, count]) => ({keyword, count}))
  .sort((a, b) => d3.descending(a.count, b.count))
```

```js
Plot.plot({
  marks: [
    Plot.barX(kwData, {x: "count", y: "keyword", fill: "#4e79a7", tip: true}),
    Plot.ruleX([0]),
  ],
  y: {label: null},
  x: {label: "Press releases"},
  width,
  marginLeft: 160,
})
```

(function () {
  const data = window.WEATHER_CHART_DATA;
  if (!data) {
    return;
  }

  const state = {
    mode: "temperature",
    range: "last-3-months",
    selectedYears: new Set(data.defaultYears || []),
    indexMap: data.labels.map((_, index) => index),
    labels: data.labels.slice(),
  };

  const svg = document.getElementById("weatherChart");
  const chartEmpty = document.getElementById("chartEmpty");
  const chartTooltip = document.getElementById("chartTooltip");
  const title = document.getElementById("pageTitle");
  const metaInfo = document.getElementById("metaInfo");
  const yearFilter = document.getElementById("yearFilter");
  const rangeFilter = document.getElementById("rangeFilter");
  const modeFilter = document.getElementById("modeFilter");

  const rangeOptions = [
    { key: "full", label: "全年" },
    { key: "first-half", label: "上半年" },
    { key: "second-half", label: "下半年" },
    { key: "last-3-months", label: "最近 3 个月" },
  ];

  const modeOptions = [
    { key: "temperature", label: "温度" },
    { key: "humidity", label: "湿度" },
  ];

  const baseColors = {
    "6": getComputedStyle(document.documentElement).getPropertyValue("--line-6").trim(),
    "12": getComputedStyle(document.documentElement).getPropertyValue("--line-12").trim(),
    "20": getComputedStyle(document.documentElement).getPropertyValue("--line-20").trim(),
  };

  const modeConfig = {
    temperature: { key: "temperature", title: "温度 (°C)", suffix: "°C" },
    humidity: { key: "humidity", title: "湿度 (%)", suffix: "%" },
  };

  function parseColor(color) {
    const rgbMatch = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    if (rgbMatch) {
      return {
        r: Number(rgbMatch[1]),
        g: Number(rgbMatch[2]),
        b: Number(rgbMatch[3]),
      };
    }

    if (color.startsWith("#")) {
      let hex = color.slice(1);
      if (hex.length === 3) {
        hex = hex.split("").map((char) => char + char).join("");
      }
      if (hex.length === 6) {
        return {
          r: parseInt(hex.slice(0, 2), 16),
          g: parseInt(hex.slice(2, 4), 16),
          b: parseInt(hex.slice(4, 6), 16),
        };
      }
    }

    return { r: 0, g: 0, b: 0 };
  }

  function withAlpha(color, alpha) {
    const rgb = parseColor(color);
    return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function dayOfYear(year, month, day) {
    const date = new Date(year, month - 1, day);
    const start = new Date(year, 0, 1);
    return Math.floor((date - start) / 86400000) + 1;
  }

  function buildYearAlphaMap(selectedYears) {
    const ordered = [...selectedYears].sort((a, b) => Number(a) - Number(b));
    const map = {};
    ordered.forEach((year, index) => {
      const stepsFromLatest = ordered.length - 1 - index;
      map[year] = Math.max(0.35, 1 - 0.55 * stepsFromLatest);
    });
    return map;
  }

  function buildDatasets() {
    const alphaByYear = buildYearAlphaMap(state.selectedYears);
    const datasets = [];

    [...state.selectedYears].sort((a, b) => Number(a) - Number(b)).forEach((year) => {
      data.hours.forEach((hour) => {
        datasets.push({
          year,
          hour,
          label: `${data.hourLabels[hour]} · ${year}`,
          color: withAlpha(baseColors[hour], alphaByYear[year] || 1),
          values: data.series[state.mode][year]?.[hour] || [],
        });
      });
    });

    return datasets;
  }

  function getRangeIndices() {
    if (state.range === "full") {
      return data.labels.map((_, index) => index);
    }

    const months = data.labels.map((label) => Number(label.split("-")[0]));
    if (state.range === "first-half") {
      return months.map((month, index) => (month <= 6 ? index : null)).filter((value) => value !== null);
    }
    if (state.range === "second-half") {
      return months.map((month, index) => (month >= 7 ? index : null)).filter((value) => value !== null);
    }

    const today = new Date();
    const start = new Date(today);
    start.setMonth(start.getMonth() - 3);

    const labelDayOfYear = data.labels.map((label) => {
      const [month, day] = label.split("-").map(Number);
      return dayOfYear(data.baseYear, month, day);
    });
    const startDoy = dayOfYear(data.baseYear, start.getMonth() + 1, start.getDate());
    const endDoy = dayOfYear(data.baseYear, today.getMonth() + 1, today.getDate());

    if (startDoy <= endDoy) {
      return labelDayOfYear.map((doy, index) => (doy >= startDoy && doy <= endDoy ? index : null)).filter((value) => value !== null);
    }

    return labelDayOfYear
      .map((doy, index) => (doy >= startDoy || doy <= endDoy ? index : null))
      .filter((value) => value !== null);
  }

  function buildPath(points) {
    let path = "";
    let started = false;
    points.forEach((point) => {
      if (!point) {
        started = false;
        return;
      }
      path += `${started ? "L" : "M"} ${point.x.toFixed(2)} ${point.y.toFixed(2)} `;
      started = true;
    });
    return path.trim();
  }

  function renderMeta() {
    title.textContent = data.title;
    metaInfo.innerHTML = [
      `<span>更新于: ${escapeHtml(data.generatedAt)} (${escapeHtml(data.timezone)})</span>`,
      `<span>06:00 记录 ${data.counts["6"] || 0} 条</span>`,
      `<span>12:00 记录 ${data.counts["12"] || 0} 条</span>`,
      `<span>20:00 记录 ${data.counts["20"] || 0} 条</span>`,
    ].join("");
  }

  function renderYearFilter() {
    yearFilter.innerHTML = `<span>年份</span>${data.years.map((year) => `
      <label class="year-chip">
        <input type="checkbox" value="${year}" ${state.selectedYears.has(year) ? "checked" : ""} />
        <span>${year}</span>
      </label>
    `).join("")}`;

    yearFilter.querySelectorAll("input").forEach((input) => {
      input.addEventListener("change", () => {
        if (input.checked) {
          state.selectedYears.add(input.value);
        } else {
          state.selectedYears.delete(input.value);
        }
        renderChart();
      });
    });
  }

  function renderButtons(container, options, activeKey, onClick) {
    container.innerHTML = options.map((option) => `
      <button class="tab ${option.key === activeKey ? "is-active" : ""}" data-key="${option.key}">${option.label}</button>
    `).join("");
    container.querySelectorAll(".tab").forEach((button) => {
      button.addEventListener("click", () => onClick(button.dataset.key));
    });
  }

  function renderControls() {
    renderButtons(rangeFilter, rangeOptions, state.range, (key) => {
      state.range = key;
      renderControls();
      renderChart();
    });

    renderButtons(modeFilter, modeOptions, state.mode, (key) => {
      state.mode = key;
      renderControls();
      renderChart();
    });
  }

  function hideTooltip() {
    chartTooltip.classList.remove("is-visible");
  }

  function showTooltip(event, text) {
    const wrapRect = svg.parentElement.getBoundingClientRect();
    chartTooltip.textContent = text;
    chartTooltip.classList.add("is-visible");

    const tooltipRect = chartTooltip.getBoundingClientRect();
    let left = event.clientX - wrapRect.left + 12;
    let top = event.clientY - wrapRect.top - tooltipRect.height - 12;

    if (left + tooltipRect.width > wrapRect.width - 8) {
      left = wrapRect.width - tooltipRect.width - 8;
    }
    if (left < 8) {
      left = 8;
    }
    if (top < 8) {
      top = event.clientY - wrapRect.top + 12;
    }

    chartTooltip.style.left = `${left}px`;
    chartTooltip.style.top = `${top}px`;
  }

  function renderChart() {
    state.indexMap = getRangeIndices();
    state.labels = state.indexMap.map((index) => data.labels[index]);

    const datasets = buildDatasets().map((dataset) => ({
      ...dataset,
      values: state.indexMap.map((index) => dataset.values[index]),
    }));

    const numericValues = datasets.flatMap((dataset) => dataset.values.filter((value) => typeof value === "number"));
    const wrap = svg.parentElement;
    const width = Math.max(320, Math.floor(wrap.clientWidth));
    const height = Math.max(280, Math.floor(wrap.clientHeight));

    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    if (!numericValues.length) {
      chartEmpty.style.display = "flex";
      svg.innerHTML = "";
      hideTooltip();
      return;
    }

    chartEmpty.style.display = "none";

    let minValue = Math.min(...numericValues);
    let maxValue = Math.max(...numericValues);
    if (minValue === maxValue) {
      minValue -= 1;
      maxValue += 1;
    }
    const padding = Math.max(1, (maxValue - minValue) * 0.12);
    minValue -= padding;
    maxValue += padding;

    const margin = { top: 72, right: 24, bottom: 58, left: 58 };
    const innerWidth = Math.max(40, width - margin.left - margin.right);
    const innerHeight = Math.max(40, height - margin.top - margin.bottom);
    const xStep = state.labels.length > 1 ? innerWidth / (state.labels.length - 1) : 0;
    const xForIndex = (index) => margin.left + xStep * index;
    const yForValue = (value) => margin.top + ((maxValue - value) / (maxValue - minValue)) * innerHeight;
    const ticks = Array.from({ length: 6 }, (_, index) => minValue + ((maxValue - minValue) * index) / 5);
    const xTickStep = Math.max(1, Math.ceil(state.labels.length / 8));
    const suffix = modeConfig[state.mode].suffix;

    const grid = ticks.map((tick) => {
      const y = yForValue(tick);
      return `
        <line x1="${margin.left}" y1="${y.toFixed(2)}" x2="${width - margin.right}" y2="${y.toFixed(2)}" stroke="rgba(120,130,140,0.18)" stroke-width="1" />
        <text x="${margin.left - 10}" y="${(y + 5).toFixed(2)}" text-anchor="end" fill="#5a6670" font-size="12">${Math.round(tick)}${suffix}</text>
      `;
    }).join("");

    const xAxis = state.labels.map((label, index) => {
      if (index % xTickStep !== 0 && index !== state.labels.length - 1) {
        return "";
      }
      return `<text x="${xForIndex(index).toFixed(2)}" y="${height - 18}" text-anchor="middle" fill="#5a6670" font-size="12">${label}</text>`;
    }).join("");

    const legend = datasets.map((dataset, index) => {
      const x = margin.left + (index % 3) * Math.max(180, innerWidth / 3);
      const y = 26 + Math.floor(index / 3) * 24;
      return `
        <circle cx="${x}" cy="${y}" r="5" fill="${dataset.color}" />
        <text x="${x + 12}" y="${y + 4}" fill="#1b1f23" font-size="13">${dataset.label}</text>
      `;
    }).join("");

    const lines = datasets.map((dataset) => {
      const points = dataset.values.map((value, index) => {
        if (value === null || value === undefined) {
          return null;
        }
        return { x: xForIndex(index), y: yForValue(value), value };
      });
      const path = buildPath(points);
      if (!path) {
        return "";
      }

      const markers = points.map((point, index) => {
        if (!point) {
          return "";
        }
        const rawIndex = state.indexMap[index];
        const humidity = data.series.humidity[dataset.year]?.[dataset.hour]?.[rawIndex];
        const weather = data.series.weather[dataset.year]?.[dataset.hour]?.[rawIndex] || "未知";
        const detail = [
          dataset.label,
          `日期: ${dataset.year}-${state.labels[index]} ${data.hourLabels[dataset.hour]}`,
          `${modeConfig[state.mode].title}: ${point.value}${suffix}`,
          `湿度: ${humidity === null || humidity === undefined ? "无数据" : `${humidity}%`}`,
          `天气: ${weather}`,
        ].join("\n");
        return `
          <circle
            cx="${point.x.toFixed(2)}"
            cy="${point.y.toFixed(2)}"
            r="7"
            fill="transparent"
            data-tooltip="${escapeHtml(detail)}"
          ></circle>
        `;
      }).join("");

      return `
        <path d="${path}" fill="none" stroke="${dataset.color}" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round" />
        ${markers}
      `;
    }).join("");

    svg.innerHTML = `
      <rect x="0" y="0" width="${width}" height="${height}" fill="transparent" />
      ${grid}
      <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" stroke="rgba(27,31,35,0.2)" stroke-width="1" />
      <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" stroke="rgba(27,31,35,0.2)" stroke-width="1" />
      <text x="${margin.left}" y="${margin.top - 26}" fill="#5a6670" font-size="13">${modeConfig[state.mode].title}</text>
      ${legend}
      ${lines}
      ${xAxis}
    `;

    svg.querySelectorAll("[data-tooltip]").forEach((node) => {
      node.addEventListener("mouseenter", (event) => {
        showTooltip(event, node.dataset.tooltip || "");
      });
      node.addEventListener("mousemove", (event) => {
        showTooltip(event, node.dataset.tooltip || "");
      });
      node.addEventListener("mouseleave", hideTooltip);
    });
  }

  renderMeta();
  renderYearFilter();
  renderControls();
  window.addEventListener("resize", renderChart);
  window.addEventListener("scroll", hideTooltip, { passive: true });
  renderChart();
})();

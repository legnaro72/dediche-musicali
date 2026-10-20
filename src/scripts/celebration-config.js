export const CELEBRATION_TEXT_LIMIT = 120;

export function normalizeCelebration(value) {
  const raw = value && typeof value === 'object' ? value : {};
  const text = typeof raw.text === 'string' ? Array.from(raw.text.trim().replace(/\s+/gu, ' ')).slice(0, CELEBRATION_TEXT_LIMIT).join('') : '';
  let duration = typeof raw.duration === 'number' || (typeof raw.duration === 'string' && raw.duration.trim()) ? Number(raw.duration) : 10;
  if (!Number.isFinite(duration)) duration = 10;
  return { enabled: raw.enabled === true && Boolean(text), text, duration: Math.max(3, Math.min(30, Math.trunc(duration))) };
}

// Split overlong words at grapheme boundaries, keeping emoji and accents intact.
export function fitCelebrationText(ctx, text, width, height, family) {
  const split = value => typeof Intl.Segmenter === 'function'
    ? Array.from(new Intl.Segmenter(undefined, { granularity: 'grapheme' }).segment(value), part => part.segment) : Array.from(value);
  const words = text.split(' ');
  const maxLines = Array.from(text).length <= 32 ? 2 : 6;
  const fit = size => {
    ctx.font = `800 ${size}px ${family}`;
    const lines = [];
    let line = '';
    for (const word of words) {
      const combined = line ? `${line} ${word}` : word;
      if (ctx.measureText(combined).width <= width * .88) { line = combined; continue; }
      if (line) { lines.push(line); line = ''; }
      for (const glyph of split(word)) {
        if (line && ctx.measureText(line + glyph).width > width * .88) { lines.push(line); line = ''; }
        line += glyph;
      }
    }
    if (line) lines.push(line);
    const lineHeight = size * 1.16;
    const wholeWords = words.every(word => split(word).length > 24 || ctx.measureText(word).width <= width * .88);
    return { lines, size, lineHeight, family, wholeWords };
  };
  let low = 6, high = Math.max(6, Math.floor(Math.min(320, width * .85, height * .65)));
  let result = fit(low);
  while (low <= high) {
    const size = Math.floor((low + high) / 2);
    const candidate = fit(size);
    if (candidate.wholeWords && candidate.lines.length <= maxLines && candidate.lines.length * candidate.lineHeight <= height * .7) { result = candidate; low = size + 1; }
    else high = size - 1;
  }
  return result;
}

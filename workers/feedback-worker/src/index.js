const REACTION_KEYS = ['down', 'like', 'heart', 'sun'];

function allowedCorsOrigin(request, env = {}) {
  const requestOrigin = request?.headers?.get('origin') || '';
  const configured = String(env.ALLOWED_ORIGINS || env.ALLOWED_ORIGIN || '*')
    .split(',')
    .map(origin => origin.trim())
    .filter(Boolean);
  if (configured.includes('*')) return '*';
  if (requestOrigin && configured.includes(requestOrigin)) return requestOrigin;
  return configured[0] || '*';
}

function jsonResponse(payload, status = 200, env = {}, request = null) {
  const origin = allowedCorsOrigin(request, env);
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'access-control-allow-origin': origin,
      'access-control-allow-methods': 'GET, POST, OPTIONS',
      'access-control-allow-headers': 'content-type',
      'cache-control': 'no-store',
      vary: 'Origin',
    },
  });
}

function normalizeReactions(value) {
  const source = value && typeof value === 'object' ? value : {};
  return REACTION_KEYS.reduce((acc, key) => {
    const count = Number(source[key] || 0);
    acc[key] = Number.isFinite(count) ? Math.max(0, Math.trunc(count)) : 0;
    return acc;
  }, {});
}

function ensureFeedbackFields(dedication) {
  return {
    ...dedication,
    votoPilly: dedication.votoPilly ?? null,
    pensieroPilly: dedication.pensieroPilly ?? '',
    reactions: normalizeReactions(dedication.reactions),
  };
}

function feedbackPayload(dedication) {
  const normalized = ensureFeedbackFields(dedication);
  return {
    id: normalized.id || '',
    date: normalized.date || '',
    title: normalized.song_title || '',
    artist: normalized.artist || '',
    votoPilly: normalized.votoPilly,
    pensieroPilly: normalized.pensieroPilly || '',
    reactions: normalizeReactions(normalized.reactions),
    updated_at: normalized.updated_at || '',
  };
}

function requiredEnv(env, key) {
  const value = env[key];
  if (!value) throw new Error(`Secret/variabile mancante: ${key}`);
  return value;
}

function githubHeaders(env) {
  return {
    accept: 'application/vnd.github+json',
    authorization: `Bearer ${requiredEnv(env, 'GITHUB_TOKEN')}`,
    'x-github-api-version': '2022-11-28',
    'user-agent': 'ddgpilli-feedback-worker',
  };
}

function githubRepo(env) {
  return requiredEnv(env, 'GITHUB_REPO');
}

function githubBranch(env) {
  return env.GITHUB_BRANCH || 'main';
}

async function githubRequest(env, path, options = {}) {
  const response = await fetch(`https://api.github.com/repos/${githubRepo(env)}/${path.replace(/^\/+/, '')}`, {
    ...options,
    headers: {
      ...githubHeaders(env),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`GitHub API ${response.status}: ${text}`);
  }
  return response;
}

function decodeBase64Utf8(value) {
  const binary = atob(value.replace(/\s/g, ''));
  const bytes = Uint8Array.from(binary, char => char.charCodeAt(0));
  return new TextDecoder('utf-8').decode(bytes).replace(/^\uFEFF/, '');
}

function encodeBase64Utf8(value) {
  const bytes = new TextEncoder().encode(value);
  let binary = '';
  bytes.forEach(byte => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

async function loadDedicationPath(env, repoPath) {
  const response = await githubRequest(
    env,
    `contents/${repoPath}`,
    { method: 'GET', cf: { cacheTtl: 0 }, headers: {} },
  );
  const payload = await response.json();
  const dedication = JSON.parse(decodeBase64Utf8(payload.content));
  return {
    dedication: ensureFeedbackFields(dedication),
    path: payload.path,
    sha: payload.sha,
  };
}

async function listDedicationFiles(env) {
  const response = await githubRequest(
    env,
    `contents/data/dedications?ref=${encodeURIComponent(githubBranch(env))}`,
    { method: 'GET', cf: { cacheTtl: 0 } },
  );
  const items = await response.json();
  return items.filter(item => item.type === 'file' && item.name.endsWith('.json'));
}

async function loadDedicationById(env, dedicationId) {
  if (!dedicationId) throw new Error('dedication_id obbligatorio.');

  const directPath = `data/dedications/${dedicationId}.json`;
  try {
    return await loadDedicationPath(env, `${directPath}?ref=${encodeURIComponent(githubBranch(env))}`);
  } catch {
    // Compatibilita' con file legacy chiamati per data ma con id interno completo.
  }

  const files = await listDedicationFiles(env);
  for (const file of files) {
    const loaded = await loadDedicationPath(env, `${file.path}?ref=${encodeURIComponent(githubBranch(env))}`);
    if (loaded.dedication.id === dedicationId) return loaded;
  }

  throw new Error(`Dedica non trovata: ${dedicationId}`);
}

async function saveDedication(env, loaded, message) {
  const content = encodeBase64Utf8(JSON.stringify(loaded.dedication, null, 2));
  const response = await githubRequest(env, `contents/${loaded.path}`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      message,
      content,
      sha: loaded.sha,
      branch: githubBranch(env),
    }),
  });
  await response.json();
  return loaded.dedication;
}

function nowIsoRomeApprox() {
  return new Date().toISOString();
}

function romeDateTimeParts(date = new Date()) {
  const parts = new Intl.DateTimeFormat('it-IT', {
    timeZone: 'Europe/Rome',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(date).reduce((acc, part) => {
    acc[part.type] = part.value;
    return acc;
  }, {});
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    time: `${parts.hour}:${parts.minute}:${parts.second}`,
  };
}

function truncateInput(value, maxLength) {
  const text = String(value || '').trim();
  return text.length <= maxLength ? text : `${text.slice(0, maxLength - 1)}…`;
}

async function dispatchVoteEmail(env, feedback) {
  const workflow = env.VOTE_EMAIL_WORKFLOW_FILE || 'vote-email-notification.yml';
  const when = romeDateTimeParts(new Date());
  const response = await githubRequest(env, `actions/workflows/${workflow}/dispatches`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      ref: githubBranch(env),
      inputs: {
        date: when.date,
        time: when.time,
        score: String(feedback.votoPilly ?? ''),
        thought: truncateInput(feedback.pensieroPilly || '', 6000),
        title: truncateInput(feedback.title || '', 200),
        artist: truncateInput(feedback.artist || '', 200),
      },
    }),
  });
  if (response.status !== 204) await response.text();
}

async function getFeedback(env, dedicationId) {
  const loaded = await loadDedicationById(env, dedicationId);
  return feedbackPayload(loaded.dedication);
}

async function getAllFeedback(env) {
  const files = await listDedicationFiles(env);
  const feedback = {};
  for (const file of files) {
    const loaded = await loadDedicationPath(env, `${file.path}?ref=${encodeURIComponent(githubBranch(env))}`);
    const payload = feedbackPayload(loaded.dedication);
    if (payload.id) feedback[payload.id] = payload;
  }
  return feedback;
}

async function saveVote(env, payload) {
  const dedicationId = String(payload.id || payload.dedicationId || '').trim();
  const vote = Number(payload.votoPilly);
  if (!Number.isInteger(vote) || vote < 1 || vote > 10) {
    throw new Error('votoPilly deve essere un numero intero da 1 a 10.');
  }

  const loaded = await loadDedicationById(env, dedicationId);
  loaded.dedication.votoPilly = vote;
  loaded.dedication.pensieroPilly = String(payload.pensieroPilly || '').trim();
  loaded.dedication.updated_at = nowIsoRomeApprox();
  await saveDedication(env, loaded, `Salva voto Pilly ${dedicationId}`);
  const feedback = feedbackPayload(loaded.dedication);
  try {
    await dispatchVoteEmail(env, feedback);
    feedback.vote_email_dispatched = true;
  } catch (error) {
    console.warn('Email voto Pilly non inviata:', error);
    feedback.vote_email_dispatched = false;
  }
  return feedback;
}

async function saveReaction(env, payload) {
  const dedicationId = String(payload.id || payload.dedicationId || '').trim();
  const reaction = payload.reaction === null || payload.reaction === undefined
    ? ''
    : String(payload.reaction).trim();
  const previousReaction = String(payload.previousReaction || '').trim();
  if (reaction && !REACTION_KEYS.includes(reaction)) {
    throw new Error(`reaction non valida. Usa una tra: ${REACTION_KEYS.join(', ')}`);
  }
  if (previousReaction && !REACTION_KEYS.includes(previousReaction)) {
    throw new Error(`previousReaction non valida. Usa una tra: ${REACTION_KEYS.join(', ')}`);
  }
  if (!reaction && !previousReaction) {
    throw new Error('reaction o previousReaction obbligatoria.');
  }

  const loaded = await loadDedicationById(env, dedicationId);
  const reactions = normalizeReactions(loaded.dedication.reactions);
  if (previousReaction) {
    reactions[previousReaction] = Math.max(0, reactions[previousReaction] - 1);
  }
  if (reaction) {
    reactions[reaction] += 1;
  }
  loaded.dedication.reactions = reactions;
  loaded.dedication.updated_at = nowIsoRomeApprox();
  await saveDedication(env, loaded, `Salva reazione Pilly ${dedicationId}`);
  return feedbackPayload(loaded.dedication);
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return jsonResponse({ ok: true }, 200, env, request);

    const url = new URL(request.url);
    try {
      if (request.method === 'GET' && url.pathname === '/') {
        return jsonResponse({
          ok: true,
          service: 'DDGPilli feedback worker',
          endpoints: ['/feedback/all', '/feedback?id=<dedication_id>', '/save_vote', '/save_reaction'],
        }, 200, env, request);
      }

      if (request.method === 'GET' && url.pathname === '/feedback') {
        return jsonResponse({
          ok: true,
          feedback: await getFeedback(env, url.searchParams.get('id') || url.searchParams.get('dedicationId')),
        }, 200, env, request);
      }

      if (request.method === 'GET' && url.pathname === '/feedback/all') {
        return jsonResponse({ ok: true, feedback: await getAllFeedback(env) }, 200, env, request);
      }

      if (request.method === 'POST' && url.pathname === '/save_vote') {
        const payload = await request.json();
        const feedback = await saveVote(env, payload);
        return jsonResponse({ ok: true, ...feedback }, 200, env, request);
      }

      if (request.method === 'POST' && url.pathname === '/save_reaction') {
        const payload = await request.json();
        const feedback = await saveReaction(env, payload);
        return jsonResponse({ ok: true, ...feedback }, 200, env, request);
      }

      return jsonResponse({ ok: false, error: 'Endpoint non trovato.' }, 404, env, request);
    } catch (error) {
      return jsonResponse({
        ok: false,
        error: error instanceof Error ? error.message : 'Errore feedback worker.',
      }, 400, env, request);
    }
  },
};

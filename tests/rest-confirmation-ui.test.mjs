import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash, webcrypto } from 'node:crypto'
import { runInNewContext } from 'node:vm'
import { TextEncoder } from 'node:util'

const html = await readFile(new URL('../src/micro_helper/static/index.html', import.meta.url), 'utf8')
const wrapper = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(match => match[1])
  .find(script => script.includes('const baseFetch = window.fetch.bind(window);'))
assert.ok(wrapper, 'REST confirmation wrapper must be present in the browser UI')

function createHarness({ allow = true, token = 'server-issued-one-time-token' } = {}) {
  const calls = []
  const prompts = []
  const window = {
    crypto: webcrypto,
    confirm(message) { prompts.push(message); return allow },
    async fetch(input, init = {}) {
      calls.push({ input, init })
      if (input === '/v1/actions/confirm') {
        return new Response(JSON.stringify(token ? { confirmation_token: token } : {}), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response(JSON.stringify({ ok: true }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    },
  }
  runInNewContext(wrapper, {
    window,
    location: { origin: 'http://127.0.0.1:8000', href: 'http://127.0.0.1:8000/' },
    URL, Headers, Response, Request, TextEncoder, Uint8Array, Array, JSON, Promise,
  })
  return { fetch: window.fetch, calls, prompts }
}

test('protected writes show the exact action and forward the server-issued token once', async () => {
  const harness = createHarness()
  const payload = { content: 'Odpovídej stručně', category: 'preference' }
  const response = await harness.fetch('/v1/memories', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  assert.equal(response.status, 201)
  assert.equal(harness.prompts.length, 1)
  assert.match(harness.prompts[0], /POST \/v1\/memories/)
  assert.match(harness.prompts[0], /Odpovídej stručně/)
  assert.equal(harness.calls.length, 2)
  const confirmation = JSON.parse(harness.calls[0].init.body)
  assert.deepEqual(confirmation, { method: 'POST', path: '/v1/memories', arguments: payload })
  assert.equal(new Headers(harness.calls[1].init.headers).get('X-Micro-Helper-Confirmation'), 'server-issued-one-time-token')
})

test('cancelling a protected write never contacts the API', async () => {
  const harness = createHarness({ allow: false })
  const response = await harness.fetch('/v1/conversations', { method: 'DELETE' })
  assert.equal(response.status, 409)
  assert.equal(harness.calls.length, 0)
  assert.equal(harness.prompts.length, 1)
})

test('backup restore confirmation binds exact raw request bytes without exposing backup contents', async () => {
  const harness = createHarness()
  const body = JSON.stringify({ backup: { memories: [{ content: 'private-note' }] }, confirm_replace: true })
  const response = await harness.fetch('/v1/backup/restore', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  })
  assert.equal(response.status, 201)
  const confirmation = JSON.parse(harness.calls[0].init.body)
  assert.equal(confirmation.method, 'POST')
  assert.equal(confirmation.path, '/v1/backup/restore')
  assert.deepEqual(confirmation.arguments, { body_sha256: createHash('sha256').update(body, 'utf8').digest('hex') })
  assert.equal(harness.calls[0].init.body.includes('private-note'), false)
  assert.match(harness.prompts[0], /memories: 1/)
})

test('chat sends and cross-origin requests do not trigger mutation confirmation', async () => {
  const harness = createHarness()
  await harness.fetch('/v1/chat', { method: 'POST', body: JSON.stringify({ message: 'Ahoj' }) })
  await harness.fetch('https://example.com/v1/memories', { method: 'POST', body: '{}' })
  assert.equal(harness.prompts.length, 0)
  assert.equal(harness.calls.length, 2)
})

test('a missing confirmation token fails closed without sending the mutation', async () => {
  const harness = createHarness({ token: null })
  const response = await harness.fetch('/v1/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_name: 'Micro Helper' }),
  })
  assert.equal(response.status, 403)
  assert.equal(harness.calls.length, 1)
  assert.equal(harness.calls[0].input, '/v1/actions/confirm')
})

test('Request input preserves its body and headers when the token is attached', async () => {
  const harness = createHarness()
  const body = JSON.stringify({ agent_name: 'Micro Helper' })
  const request = new Request('http://127.0.0.1:8000/v1/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'X-Existing-Header': 'keep-me' },
    body,
  })
  const response = await harness.fetch(request)
  assert.equal(response.status, 201)
  const mutation = harness.calls[1]
  assert.equal(new Headers(mutation.init.headers).get('X-Existing-Header'), 'keep-me')
  assert.equal(new Headers(mutation.init.headers).get('X-Micro-Helper-Confirmation'), 'server-issued-one-time-token')
  assert.equal(await mutation.input.clone().text(), body)
})

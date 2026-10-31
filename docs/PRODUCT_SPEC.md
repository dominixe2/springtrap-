# Product specification

Micro Helper is a personal AI agent platform, not a character app.

## Onboarding
Each user configures an independent agent: name, wake phrase, language, voice, communication style, memory preferences, optional mascot and device permissions. The mascot is optional visual presentation, never the agent's identity or intelligence.

## Memory and identity
Profiles, preferences, conversations and memories are isolated by account. Nothing is shared with another person by default. Users can inspect, correct, export and delete their memories.

## Free-first operation
Core local features must not require a paid API key or subscription. Local inference through a replaceable provider such as Ollama is preferred. Cloud inference, hosting and remote access are optional and may cost money.

## Permissions
Permissions are scoped by user, device, tool and operation. Reading is separate from writing, sending, sharing and deleting. Sensitive actions require confirmation. Every tool action is auditable and grants are revocable.

## Offline behavior
Local tasks work offline where the operating system permits. Online tasks enter a durable queue with unique IDs, retry policy and visible status. Never report queued work as completed.

## Platforms
Android is the primary interface. Windows is an optional compute and automation worker. Future integrations may include watches, tablets, headphones and smart-home devices.

## Paired agents
Pairing requires consent from both owners. Each owner controls narrowly scoped permissions. Messages are explicitly labeled as AI-agent-mediated.

## Mascots
Mascots are optional, selectable and replaceable. Springtrap is removed from the product and must not appear as a default identity or required feature.
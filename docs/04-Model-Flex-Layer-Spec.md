# Model Flex Layer Spec

## 1. Goal

Provide a single abstraction for all model usage so the app can:

- Route tasks to `cheap`, `balanced`, or `premium` profiles.
- Swap underlying providers/models without touching business logic.
- Support:
  - Chat models (generation)
  - Embedding models
  - Optional rerankers

## 2. Concepts

### 2.1 Model Profiles

User-visible profiles:

- `cheap` — low-cost, acceptable quality.
- `balanced` — mid-range quality/cost.
- `premium` — best reasoning & quality for critical artifacts.

Each profile resolves to a concrete model in config.

### 2.2 Provider Types

- `openai`
- `anthropic`
- `gateway` (e.g., OpenRouter/OpenLLM-style)
- `local` (e.g., OpenLLM/vLLM served from our infra)

### 2.3 ModelConfig Schema (conceptual)

```ts
type ModelProvider = 'openai' | 'anthropic' | 'gateway' | 'local';

type ModelType = 'chat' | 'embedding' | 'reranker';

type ModelConfig = {
  id: string;               // e.g., 'gpt-5.1-thinking'
  provider: ModelProvider;
  type: ModelType;
  profile?: 'cheap' | 'balanced' | 'premium'; // optional
  modelName: string;        // provider-specific name
  apiKeyRef: string;        // environment variable or secret key reference
  maxTokens: number;
  costPer1kTokens?: number;
  extraConfig?: Record<string, any>;
};
models:
  - id: gpt-5.1-thinking
    provider: openai
    type: chat
    profile: premium
    modelName: gpt-5.1-thinking
    apiKeyRef: OPENAI_API_KEY
    maxTokens: 16000

  - id: cheap-assistant
    provider: gateway
    type: chat
    profile: cheap
    modelName: some-oss-model
    apiKeyRef: GATEWAY_API_KEY
    maxTokens: 4096

  - id: text-embed-main
    provider: openai
    type: embedding
    modelName: text-embedding-3-large
    apiKeyRef: OPENAI_API_KEY
    maxTokens: 8192
type Message = { role: 'system' | 'user' | 'assistant'; content: string };

type GenerateOptions = {
  modelProfile?: 'cheap' | 'balanced' | 'premium';
  modelId?: string; // optional override
  messages: Message[];
  maxTokens?: number;
  temperature?: number;
  metadata?: Record<string, any>; // for logging
};

type GenerateResult = {
  content: string;
  raw?: any;
};

interface ModelService {
  generate(opts: GenerateOptions): Promise<GenerateResult>;
}
type EmbedOptions = {
  modelId?: string; // usually a dedicated embedding model
  texts: string[];
  metadata?: Record<string, any>;
};

type EmbedResult = {
  vectors: number[][];
};

interface ModelService {
  embed(opts: EmbedOptions): Promise<EmbedResult>;
}
type RerankItem = { id: string; text: string };

type RerankOptions = {
  modelId?: string;
  query: string;
  items: RerankItem[];
};

type RerankResultItem = RerankItem & { score: number };

interface ModelService {
  rerank(opts: RerankOptions): Promise<RerankResultItem[]>;
}

====

Steps:

1. Highlight everything **between** the `====` lines (including the ```md and closing ```).
2. Copy it.
3. Go back to your **blank** TextEdit doc.
4. Paste.

Ignore the `====` lines themselves; they’re just markers in this message.

---

## Step 3 – Save the file into `docs`

1. With that text in TextEdit, press **⌘ + S**.
2. In the save window:
   - Navigate to: `Desktop → mini-rag → docs`
   - File name: `04-Model-Flex-Layer-Spec.md`
3. Click **Save**.

You should now have **three files** in `docs`.

When that’s done, just tell me:

> `Model flex file saved`

and I won’t introduce any new docs until then.
::contentReference[oaicite:0]{index=0}

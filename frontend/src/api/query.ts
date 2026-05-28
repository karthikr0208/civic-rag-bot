export interface AnswerSection {
  text: string
  tooltip_text: string
  page_refs: number[]
}

export interface Citation {
  page: number
  section: string
  label: string
  url: string
}

export interface QueryResponse {
  answer_sections: AnswerSection[]
  citations: Citation[]
  suggested_questions: string[]
}

export async function submitQuery(question: string): Promise<QueryResponse> {
  const response = await fetch('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!response.ok) {
    const text = await response.text().catch(() => '')
    throw new Error(`${response.status}: ${text || response.statusText}`)
  }
  return response.json()
}

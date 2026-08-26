import { baseApi } from '../../api/baseApi'

export interface Summary {
    total_requests: number
    block_rate: number
    avg_latency_ms: number
    total_cost_usd: number
    cost_saved_by_routing_usd: number
    cache_hit_rate: number
    blocked_requests: number
    review_requests: number
    cost_saved_usd: number
    tokens_saved: number
    cache_hits: number
}

export interface RequestRow {
    id: string
    timestamp: string
    principal_id: string
    prompt: string
    response: string
    verdict: string
    latency_ms: number
    cost_usd: number
    tokens_saved: number
    savings_usd: number
}

export interface Review {
    review_id: string
    prompt: string
    proposed_response: string
    flagged_reason: string
    risk_score: number
    created_at: string
}

export interface ReviewDecisionResult {
    review_id: string
    action_taken: string
    final_response: string
    resolved_by: string
}

export interface Budget {
    configured: boolean
    monthly_limit_usd?: number
    spent_usd?: number
    remaining_usd?: number
    request_count?: number
    blocked_count?: number
}

export const dashboardApi = baseApi.injectEndpoints({
    endpoints: (builder) => ({
        summary: builder.query<Summary, void>({
            query: () => '/v1/analytics/summary',
            providesTags: ['Summary'],
        }),
        requests: builder.query<RequestRow[], { limit?: number } | void>({
            query: (arg) => `/v1/analytics/requests${arg?.limit ? `?limit=${arg.limit}` : ''}`,
            providesTags: ['Requests'],
        }),
        budget: builder.query<Budget, void>({
            query: () => '/v1/budget',
            providesTags: ['Budget'],
        }),
        reviewQueue: builder.query<Review[], void>({
            query: () => '/v1/admin/reviews',
            providesTags: ['Reviews'],
        }),
        resolveReview: builder.mutation<
            ReviewDecisionResult,
            { reviewId: string; action: 'approve' | 'edit' | 'override'; edited_content?: string }
        >({
            query: ({ reviewId, action, edited_content }) => ({
                url: `/v1/admin/reviews/${reviewId}/resolve`,
                method: 'POST',
                body: { action, edited_content },
            }),
            invalidatesTags: ['Reviews', 'Summary'],
        }),
    }),
})

export const {
    useSummaryQuery,
    useRequestsQuery,
    useBudgetQuery,
    useReviewQueueQuery,
    useResolveReviewMutation,
} = dashboardApi

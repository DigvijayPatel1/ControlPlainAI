import { baseApi } from '../../api/baseApi';
export const dashboardApi = baseApi.injectEndpoints({
    endpoints: (builder) => ({
        summary: builder.query({
            query: () => '/v1/analytics/summary',
            providesTags: ['Summary'],
        }),
        requests: builder.query({
            query: (arg) => `/v1/analytics/requests${arg?.limit ? `?limit=${arg.limit}` : ''}`,
            providesTags: ['Requests'],
        }),
        budget: builder.query({
            query: () => '/v1/budget',
            providesTags: ['Budget'],
        }),
        reviewQueue: builder.query({
            query: () => '/v1/admin/reviews',
            providesTags: ['Reviews'],
        }),
        resolveReview: builder.mutation({
            query: ({ reviewId, action, edited_content }) => ({
                url: `/v1/admin/reviews/${reviewId}/resolve`,
                method: 'POST',
                body: { action, edited_content },
            }),
            invalidatesTags: ['Reviews', 'Summary'],
        }),
    }),
});
export const { useSummaryQuery, useRequestsQuery, useBudgetQuery, useReviewQueueQuery, useResolveReviewMutation, } = dashboardApi;

import { baseApi } from '../../api/baseApi';
export const authApi = baseApi.injectEndpoints({
    endpoints: (builder) => ({
        register: builder.mutation({
            query: (body) => ({ url: '/auth/register', method: 'POST', body }),
            invalidatesTags: ['Me'],
        }),
        login: builder.mutation({
            query: (body) => ({ url: '/auth/login', method: 'POST', body }),
            invalidatesTags: ['Me'],
        }),
        me: builder.query({
            query: () => '/auth/me',
            providesTags: ['Me'],
        }),
        rotateApiKey: builder.mutation({
            query: () => ({ url: '/auth/api-key/rotate', method: 'POST' }),
        }),
    }),
});
export const { useRegisterMutation, useLoginMutation, useMeQuery, useRotateApiKeyMutation } = authApi;

import { baseApi } from '../../api/baseApi'
import type { AuthUser, IssuedApiKey } from './authSlice'

export interface AuthResponse {
    access_token: string
    token_type: string
    user: AuthUser
    api_key: IssuedApiKey | null
}

export interface RotateResponse {
    api_key: IssuedApiKey
}

export const authApi = baseApi.injectEndpoints({
    endpoints: (builder) => ({
        register: builder.mutation<AuthResponse, { email: string; full_name: string; password: string }>({
            query: (body) => ({ url: '/auth/register', method: 'POST', body }),
            invalidatesTags: ['Me'],
        }),
        login: builder.mutation<AuthResponse, { email: string; password: string }>({
            query: (body) => ({ url: '/auth/login', method: 'POST', body }),
            invalidatesTags: ['Me'],
        }),
        me: builder.query<AuthUser, void>({
            query: () => '/auth/me',
            providesTags: ['Me'],
        }),
        rotateApiKey: builder.mutation<RotateResponse, void>({
            query: () => ({ url: '/auth/api-key/rotate', method: 'POST' }),
        }),
    }),
})

export const { useRegisterMutation, useLoginMutation, useMeQuery, useRotateApiKeyMutation } = authApi

import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import type { RootState } from '../app/store'

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export const baseApi = createApi({
    reducerPath: 'api',
    baseQuery: fetchBaseQuery({
        baseUrl: API_BASE,
        prepareHeaders: (headers, { getState }) => {
            const token = (getState() as RootState).auth.token
            if (token) headers.set('Authorization', `Bearer ${token}`)
            return headers
        },
    }),
    tagTypes: ['Summary', 'Requests', 'Reviews', 'Budget', 'Me'],
    endpoints: () => ({}),
})

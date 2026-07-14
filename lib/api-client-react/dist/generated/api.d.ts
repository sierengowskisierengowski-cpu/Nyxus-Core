import type { QueryKey, UseQueryOptions, UseQueryResult } from "@tanstack/react-query";
import type { HealthStatus, NyxusAccountStatus } from "./api.schemas";
import { customFetch } from "../custom-fetch";
import type { ErrorType } from "../custom-fetch";
type AwaitedInput<T> = PromiseLike<T> | T;
type Awaited<O> = O extends AwaitedInput<infer T> ? T : never;
type SecondParameter<T extends (...args: never) => unknown> = Parameters<T>[1];
/**
 * Returns server health status
 * @summary Health check
 */
export declare const getHealthCheckUrl: () => string;
export declare const healthCheck: (options?: RequestInit) => Promise<HealthStatus>;
export declare const getHealthCheckQueryKey: () => readonly ["/api/healthz"];
export declare const getHealthCheckQueryOptions: <TData = Awaited<ReturnType<typeof healthCheck>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof healthCheck>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof healthCheck>>, TError, TData> & {
    queryKey: QueryKey;
};
export type HealthCheckQueryResult = NonNullable<Awaited<ReturnType<typeof healthCheck>>>;
export type HealthCheckQueryError = ErrorType<unknown>;
/**
 * @summary Health check
 */
export declare function useHealthCheck<TData = Awaited<ReturnType<typeof healthCheck>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof healthCheck>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
/**
 * Returns service descriptor for the NYXUS Account sync server.
Used by Settings → NYXUS Account to confirm the configured
endpoint is alive before pushing a bundle.

 * @summary NYXUS Account service liveness
 */
export declare const getNyxusAccountStatusUrl: () => string;
export declare const nyxusAccountStatus: (options?: RequestInit) => Promise<NyxusAccountStatus>;
export declare const getNyxusAccountStatusQueryKey: () => readonly ["/api/nyxus-account/status"];
export declare const getNyxusAccountStatusQueryOptions: <TData = Awaited<ReturnType<typeof nyxusAccountStatus>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof nyxusAccountStatus>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}) => UseQueryOptions<Awaited<ReturnType<typeof nyxusAccountStatus>>, TError, TData> & {
    queryKey: QueryKey;
};
export type NyxusAccountStatusQueryResult = NonNullable<Awaited<ReturnType<typeof nyxusAccountStatus>>>;
export type NyxusAccountStatusQueryError = ErrorType<unknown>;
/**
 * @summary NYXUS Account service liveness
 */
export declare function useNyxusAccountStatus<TData = Awaited<ReturnType<typeof nyxusAccountStatus>>, TError = ErrorType<unknown>>(options?: {
    query?: UseQueryOptions<Awaited<ReturnType<typeof nyxusAccountStatus>>, TError, TData>;
    request?: SecondParameter<typeof customFetch>;
}): UseQueryResult<TData, TError> & {
    queryKey: QueryKey;
};
export {};
//# sourceMappingURL=api.d.ts.map
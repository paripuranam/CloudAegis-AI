import { useCallback, useEffect, useRef, useState } from 'react'

export const useFetching = (fetchFn, deps = []) => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const requestIdRef = useRef(0)
  const fetchFnRef = useRef(fetchFn)
  const hasInitialized = useRef(false)
  const previousDataRef = useRef(null) // Keep track of previous successful data

  useEffect(() => {
    fetchFnRef.current = fetchFn
  }, [fetchFn])

  const refetch = useCallback(async () => {
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    
    // Only set loading on initial fetch, not on refetch to prevent flashing
    if (!hasInitialized.current) {
      setLoading(true)
    }

    try {
      const result = await fetchFnRef.current()

      if (requestIdRef.current !== requestId) {
        return
      }

      const newData = result?.data ?? null
      setData(newData)
      
      // Store successful data for later reference
      if (newData !== null) {
        previousDataRef.current = newData
      }
      
      setError(null)
      hasInitialized.current = true
    } catch (err) {
      if (requestIdRef.current !== requestId) {
        return
      }

      // Preserve existing data on error - don't clear it
      setError(err.response?.data?.detail || err.message || 'An error occurred')
      hasInitialized.current = true
      
      // Keep the previous data if new fetch failed
      if (previousDataRef.current) {
        setData(previousDataRef.current)
      }
    } finally {
      if (requestIdRef.current === requestId) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    refetch()
  }, deps)

  return { data, loading, error, refetch }
}

import { useCallback, useEffect, useRef, useState } from 'react'

/** Loads data when the component mounts and gives back a `reload` function for after changes. */
export function useLoad<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const loaderRef = useRef(loader)

  useEffect(() => {
    loaderRef.current = loader
  })

  const reload = useCallback(async () => {
    try {
      setData(await loaderRef.current())
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    }
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  return { data, error, reload }
}

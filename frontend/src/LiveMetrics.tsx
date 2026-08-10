import { useEffect, useState } from 'react'

export function PassengerCount() {
  const [riders, setRiders] = useState(1_840_000)

  useEffect(() => {
    const timer = window.setInterval(() => {
      setRiders((value) => value + Math.floor(Math.random() * 8) + 2)
    }, 3500)
    return () => window.clearInterval(timer)
  }, [])

  return <>{(riders / 1_000_000).toFixed(2)}M</>
}

export function NetworkClock() {
  const [time, setTime] = useState(() => new Date())

  useEffect(() => {
    const timer = window.setInterval(() => setTime(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  return <>{time.toLocaleTimeString('en-IN', { hour12: false })}</>
}

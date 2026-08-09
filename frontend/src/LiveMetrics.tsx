import { useEffect, useState } from 'react'

export function LiveStatus() {
  const [events, setEvents] = useState(2_400_000)

  useEffect(() => {
    const timer = window.setInterval(() => {
      setEvents((value) => value + Math.floor(Math.random() * 20) + 8)
    }, 2800)
    return () => window.clearInterval(timer)
  }, [])

  return <><i></i><span>Live data connected</span><b>{(events / 1_000_000).toFixed(2)}M</b><span>events today</span></>
}

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

import { useState } from 'react'
import { formatTime, parseTime } from '../player/time'
import { input } from './styles'

interface Props {
  label: string
  /** Milliseconds, or null when not marked yet. */
  value: number | null
  onCommit: (ms: number) => void
}

/**
 * A mm:ss.mmm text field that commits on Enter or blur. Bad input is shown and not
 * committed. The parent remounts it (via `key`) when the value changes elsewhere.
 */
export function TimeField({ label, value, onCommit }: Props) {
  const [text, setText] = useState(value === null ? '' : formatTime(value / 1000))
  const [invalid, setInvalid] = useState(false)

  const commit = () => {
    if (text.trim() === '' && value === null) return
    const ms = parseTime(text)
    if (ms === null) {
      setInvalid(true)
      return
    }
    setInvalid(false)
    if (ms !== value) onCommit(ms)
  }

  return (
    <input
      aria-label={label}
      aria-invalid={invalid}
      className={`${input} w-28 font-mono tabular-nums aria-invalid:border-red-500`}
      placeholder="mm:ss.mmm"
      value={text}
      onChange={(event) => setText(event.currentTarget.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === 'Enter') commit()
      }}
    />
  )
}

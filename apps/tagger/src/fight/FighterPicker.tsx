import type { Fighter } from '../api/types'
import type { FighterChoice } from './form'
import { input, label } from './styles'

const NEW = '__new__'

interface Props {
  corner: 'Red' | 'Blue'
  fighters: readonly Fighter[]
  value: FighterChoice | null
  onChange: (choice: FighterChoice | null) => void
}

export function FighterPicker({ corner, fighters, value, onChange }: Props) {
  const selected = value === null ? '' : value.kind === 'new' ? NEW : value.id
  return (
    <div className="flex flex-col gap-2">
      <label className={label}>
        {corner} corner
        <select
          className={input}
          value={selected}
          onChange={(event) => {
            const next = event.currentTarget.value
            if (next === '') onChange(null)
            else if (next === NEW) onChange({ kind: 'new', name: '' })
            else onChange({ kind: 'existing', id: next })
          }}
        >
          <option value="">Choose a fighter</option>
          {fighters.map((fighter) => (
            <option key={fighter.id} value={fighter.id}>
              {fighter.name}
            </option>
          ))}
          <option value={NEW}>New fighter…</option>
        </select>
      </label>
      {value?.kind === 'new' && (
        <input
          aria-label={`${corner} fighter name`}
          className={input}
          placeholder="Full name as billed"
          value={value.name}
          onChange={(event) => onChange({ kind: 'new', name: event.currentTarget.value })}
        />
      )}
    </div>
  )
}

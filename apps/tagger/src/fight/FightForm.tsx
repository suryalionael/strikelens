import { useState } from 'react'
import { api } from '../api/client'
import type { Fight, Fighter } from '../api/types'
import { FighterPicker } from './FighterPicker'
import { EMPTY_FORM, fightFormErrors, type FighterChoice, type FightFormValues } from './form'
import { input, label, primaryButton } from './styles'

interface Props {
  fighters: readonly Fighter[]
  videoFile: string | null
  onFighterCreated: (fighter: Fighter) => void
  onCreated: (fight: Fight) => void
}

export function FightForm({ fighters, videoFile, onFighterCreated, onCreated }: Props) {
  const [form, setForm] = useState<FightFormValues>(EMPTY_FORM)
  const [submitted, setSubmitted] = useState(false)
  const [saving, setSaving] = useState(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const errors = fightFormErrors(form)

  const update = (changes: Partial<FightFormValues>) => setForm((f) => ({ ...f, ...changes }))

  // A new fighter is saved first. Swap the choice to the saved fighter at once, so
  // a retry after a failed fight save does not create the fighter twice.
  const resolveFighter = async (corner: 'red' | 'blue', choice: FighterChoice) => {
    if (choice.kind === 'existing') return choice.id
    const fighter = await api.createFighter(choice.name.trim())
    onFighterCreated(fighter)
    update({ [corner]: { kind: 'existing', id: fighter.id } })
    return fighter.id
  }

  const submit = async () => {
    setSubmitted(true)
    const { red, blue } = form
    if (errors.length > 0 || red === null || blue === null) return
    setSaving(true)
    setApiError(null)
    try {
      const fight = await api.createFight({
        event: form.event.trim(),
        date: form.date,
        weight_class: form.weight_class.trim() || null,
        scheduled_rounds: form.scheduled_rounds,
        red_fighter_id: await resolveFighter('red', red),
        blue_fighter_id: await resolveFighter('blue', blue),
        video_file: videoFile,
        rounds: [],
        result: null,
      })
      onCreated(fight)
    } catch (error) {
      setApiError(error instanceof Error ? error.message : String(error))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form
      aria-label="New fight"
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault()
        void submit()
      }}
    >
      <label className={label}>
        Event
        <input
          className={input}
          placeholder="e.g. Byon Combat 40"
          value={form.event}
          onChange={(event) => update({ event: event.currentTarget.value })}
        />
      </label>
      <div className="grid grid-cols-2 gap-3">
        <label className={label}>
          Date
          <input
            type="date"
            className={input}
            value={form.date}
            onChange={(event) => update({ date: event.currentTarget.value })}
          />
        </label>
        <label className={label}>
          Scheduled rounds
          <input
            type="number"
            min={1}
            className={input}
            value={Number.isNaN(form.scheduled_rounds) ? '' : form.scheduled_rounds}
            onChange={(event) => update({ scheduled_rounds: event.currentTarget.valueAsNumber })}
          />
        </label>
      </div>
      <label className={label}>
        Weight class (optional)
        <input
          className={input}
          value={form.weight_class}
          onChange={(event) => update({ weight_class: event.currentTarget.value })}
        />
      </label>
      <FighterPicker
        corner="Red"
        fighters={fighters}
        value={form.red}
        onChange={(red) => update({ red })}
      />
      <FighterPicker
        corner="Blue"
        fighters={fighters}
        value={form.blue}
        onChange={(blue) => update({ blue })}
      />

      {submitted && errors.length > 0 && (
        <ul role="alert" className="list-inside list-disc text-xs text-red-400">
          {errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
      {apiError && (
        <p role="alert" className="text-xs text-red-400">
          {apiError}
        </p>
      )}

      <button type="submit" className={primaryButton} disabled={saving}>
        {saving ? 'Saving…' : 'Create fight'}
      </button>
    </form>
  )
}

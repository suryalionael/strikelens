import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import type { Mock } from 'vitest'
import { api } from '../api/client'
import type { Fight, Tag, TagInput } from '../api/types'
import type { RoundDraft } from '../fight/rounds'
import { PlayerContext } from '../player/PlayerContext'
import type { Player } from '../player/usePlayerState'
import { fakePlayer } from '../test/fakePlayer'
import { makeTag } from '../test/tag'
import { TagPanel } from './TagPanel'

const FIGHT = { id: 'fight-1' } as Fight
const ROUNDS: RoundDraft[] = [
  { number: 1, start_ms: 1_000, end_ms: 181_000 },
  { number: 2, start_ms: 241_000, end_ms: 421_000 },
]

let videoTime = 61.25
const video = {
  get currentTime() {
    return videoTime
  },
} as HTMLVideoElement

let player: Player
let onTagsChanged: Mock<() => void>
let created = 0

beforeEach(() => {
  videoTime = 61.25
  created = 0
  player = fakePlayer({ src: 'blob:fight', videoRef: { current: video } })
  onTagsChanged = vi.fn<() => void>()
  vi.spyOn(api, 'listTags').mockResolvedValue([makeTag()])
  vi.spyOn(api, 'createTag').mockImplementation((_id, input: TagInput) =>
    Promise.resolve(makeTag({ ...input, id: `new-${++created}` })),
  )
  vi.spyOn(api, 'updateTag').mockImplementation((_f, id, patch) =>
    Promise.resolve(makeTag({ id, ...stripUndefined(patch) })),
  )
  vi.spyOn(api, 'deleteTag').mockResolvedValue(null)
  vi.spyOn(api, 'restoreTag').mockImplementation((tag: Tag) => Promise.resolve(tag))
})

afterEach(() => {
  vi.restoreAllMocks()
})

function stripUndefined<T extends object>(obj: T): Partial<T> {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined)) as Partial<T>
}

function renderPanel() {
  return render(
    <PlayerContext value={player}>
      <TagPanel fight={FIGHT} rounds={ROUNDS} onTagsChanged={onTagsChanged} />
    </PlayerContext>,
  )
}

const undoKey = (mods: Partial<KeyboardEventInit> = { ctrlKey: true }) =>
  fireEvent.keyDown(window, { key: 'z', ...mods })

async function openEditor() {
  fireEvent.click(await screen.findByRole('button', { name: /^Edit Red kick landed body/ }))
  return screen.getByRole('region', { name: 'Edit tag' })
}

const status = () => screen.getByRole('status')

describe('editing a tag', () => {
  it('opens from the tag list and changes a field through the API', async () => {
    renderPanel()
    const editor = await openEditor()
    fireEvent.click(
      within(within(editor).getByRole('group', { name: 'Edit weapon' })).getByRole('button', {
        name: 'jab',
      }),
    )
    await waitFor(() =>
      expect(api.updateTag).toHaveBeenCalledWith('fight-1', 't1', { weapon: 'jab' }),
    )
    await waitFor(() =>
      expect(status()).toHaveTextContent('Changed to Red jab landed body at 01:01.250.'),
    )
    expect(screen.getByRole('table')).toHaveTextContent('jab · landed · body')
    expect(onTagsChanged).toHaveBeenCalledOnce()
  })

  it('opens from a timeline marker', async () => {
    renderPanel()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Red kick landed body at 01:01.250, round 1' }),
    )
    expect(player.seek).toHaveBeenCalledWith(61.25)
    expect(screen.getByRole('region', { name: 'Edit tag' })).toBeInTheDocument()
  })

  it('moves the tag to the right round when its time changes', async () => {
    renderPanel()
    const editor = await openEditor()
    const time = within(editor).getByLabelText('Tag time')
    fireEvent.change(time, { target: { value: '05:00.000' } })
    fireEvent.keyDown(time, { key: 'Enter' })
    await waitFor(() =>
      expect(api.updateTag).toHaveBeenCalledWith('fight-1', 't1', {
        timestamp_ms: 300_000,
        round: 2,
      }),
    )
  })

  it('sets the time from the video', async () => {
    renderPanel()
    const editor = await openEditor()
    videoTime = 70
    fireEvent.click(within(editor).getByRole('button', { name: 'Set to video time' }))
    await waitFor(() =>
      expect(api.updateTag).toHaveBeenCalledWith('fight-1', 't1', {
        timestamp_ms: 70_000,
        round: 1,
      }),
    )
  })

  it('refuses a time outside every round without calling the API', async () => {
    renderPanel()
    const editor = await openEditor()
    const time = within(editor).getByLabelText('Tag time')
    fireEvent.change(time, { target: { value: '03:30.000' } })
    fireEvent.keyDown(time, { key: 'Enter' })
    expect(status()).toHaveTextContent('Not changed: 03:30.000 is outside every marked round.')
    expect(api.updateTag).not.toHaveBeenCalled()
  })
})

describe('deleting a tag', () => {
  it('asks first, and Keep cancels', async () => {
    renderPanel()
    const editor = await openEditor()
    fireEvent.click(within(editor).getByRole('button', { name: 'Delete tag…' }))
    expect(within(editor).getByText('Delete this tag?')).toBeInTheDocument()
    fireEvent.click(within(editor).getByRole('button', { name: 'Keep' }))
    expect(api.deleteTag).not.toHaveBeenCalled()
    expect(within(editor).getByRole('button', { name: 'Delete tag…' })).toBeInTheDocument()
  })

  it('deletes after confirming and closes the editor', async () => {
    renderPanel()
    const editor = await openEditor()
    fireEvent.click(within(editor).getByRole('button', { name: 'Delete tag…' }))
    fireEvent.click(within(editor).getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(api.deleteTag).toHaveBeenCalledWith('fight-1', 't1'))
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Edit tag' })).toBeNull())
    expect(screen.getByText('0 tags')).toBeInTheDocument()
    expect(status()).toHaveTextContent('Deleted Red kick landed body at 01:01.250.')
  })
})

describe('undo', () => {
  it('undoes a new tag by deleting it', async () => {
    renderPanel()
    await screen.findByText('1 tags')
    for (const key of ['w', 'j', 'm', '1']) fireEvent.keyDown(window, { key })
    await screen.findByText('2 tags')
    undoKey()
    await waitFor(() => expect(api.deleteTag).toHaveBeenCalledWith('fight-1', 'new-1'))
    await screen.findByText('1 tags')
    expect(status()).toHaveTextContent('Undid: removed Blue jab missed head at 01:01.250.')
  })

  it('undoes a delete by restoring the same tag', async () => {
    renderPanel()
    const editor = await openEditor()
    fireEvent.click(within(editor).getByRole('button', { name: 'Delete tag…' }))
    fireEvent.click(within(editor).getByRole('button', { name: 'Delete' }))
    await screen.findByText('0 tags')
    undoKey({ metaKey: true })
    await waitFor(() => expect(api.restoreTag).toHaveBeenCalledWith(makeTag()))
    await screen.findByText('1 tags')
  })

  it('undoes an edit by putting every field back', async () => {
    renderPanel()
    const editor = await openEditor()
    fireEvent.click(
      within(within(editor).getByRole('group', { name: 'Edit fighter' })).getByRole('button', {
        name: 'Blue',
      }),
    )
    await waitFor(() => expect(status()).toHaveTextContent('Changed to Blue kick'))
    undoKey()
    await waitFor(() => expect(api.updateTag).toHaveBeenCalledTimes(2))
    expect(vi.mocked(api.updateTag).mock.calls[1]).toEqual([
      'fight-1',
      't1',
      {
        fighter: 'red',
        weapon: 'kick',
        outcome: 'landed',
        target: 'body',
        timestamp_ms: 61_250,
        round: 1,
        status: 'confirmed',
      },
    ])
  })

  it('undoes at least 20 steps, newest first', async () => {
    renderPanel()
    await screen.findByText('1 tags')
    for (let i = 0; i < 25; i++) {
      for (const key of ['q', 'k', 'l', '2']) fireEvent.keyDown(window, { key })
      await screen.findByText(`${i + 2} tags`)
    }
    for (let i = 0; i < 25; i++) {
      undoKey()
      await screen.findByText(`${25 - i} tags`)
    }
    const deleted = vi.mocked(api.deleteTag).mock.calls.map((c) => c[1])
    expect(deleted).toEqual(Array.from({ length: 25 }, (_, i) => `new-${25 - i}`))
    undoKey()
    await waitFor(() => expect(status()).toHaveTextContent('Nothing to undo.'))
  })

  it('keeps a failed undo so it can be retried', async () => {
    renderPanel()
    await screen.findByText('1 tags')
    for (const key of ['q', 'k', 'l', '2']) fireEvent.keyDown(window, { key })
    await screen.findByText('2 tags')
    vi.mocked(api.deleteTag).mockRejectedValueOnce(new Error('API down'))
    undoKey()
    await waitFor(() => expect(status()).toHaveTextContent('API down'))
    expect(screen.getByText('2 tags')).toBeInTheDocument()
    undoKey()
    await screen.findByText('1 tags')
    expect(api.deleteTag).toHaveBeenCalledTimes(2)
  })

  it('leaves Ctrl+Z to a text field, and ignores Ctrl+Shift+Z', async () => {
    renderPanel()
    await screen.findByText('1 tags')
    for (const key of ['q', 'k', 'l', '2']) fireEvent.keyDown(window, { key })
    await screen.findByText('2 tags')
    const input = document.createElement('input')
    document.body.append(input)
    fireEvent.keyDown(input, { key: 'z', ctrlKey: true })
    undoKey({ ctrlKey: true, shiftKey: true })
    input.remove()
    expect(api.deleteTag).not.toHaveBeenCalled()
  })

  it('says so when undo is pressed while a change is still saving', async () => {
    let finish: (tag: Tag) => void = () => undefined
    vi.mocked(api.updateTag).mockImplementationOnce(
      () => new Promise<Tag>((resolve) => (finish = resolve)),
    )
    renderPanel()
    const editor = await openEditor()
    fireEvent.click(
      within(within(editor).getByRole('group', { name: 'Edit target' })).getByRole('button', {
        name: 'head',
      }),
    )
    undoKey()
    expect(status()).toHaveTextContent('Still saving the last change.')
    finish(makeTag({ target: 'head' }))
    await waitFor(() => expect(status()).toHaveTextContent('Changed to Red kick landed head'))
  })
})

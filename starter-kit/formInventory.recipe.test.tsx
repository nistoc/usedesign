// РЕЦЕПТ производителя перечня формы (проверка №5) — «ПОД СЕБЯ» помечено, остальное готово.
// Разделение труда (issue #7): рендер компонента по состояниям — ВАШ (он знает ваш фреймворк);
// конвенция якорей и формат перечня — в коробке usedesign, чтобы проекты не изобретали
// расходящиеся конвенции в каждой копии этого файла.
//
// Конвенция data-атрибутов (доказана на двух панелях и модалке раньше, чем записана):
//   data-field       — значение, которое видит человек
//   data-section     — контейнер с именем (шапка, подвал, таблица…)
//   data-panel-head  — шапка каркаса панели (в перечне — фиксированное имя "panel-head")
//   data-action      — интерактивный контрол
//   data-control     — контейнерная разновидность контрола (меню, группа кнопок)
//
// Собирайте с document.body, если меню/оверлеи рендерятся порталом: компонент, отрисованный
// вне своего контейнера, всё равно честно отрисован. Пишет файл обычный прогон теста; в CI
// перечень порождается заново на каждый прогон и в репозитории не хранится.
import { render } from '@testing-library/react'          // ПОД СЕБЯ: ваш фреймворк
import { describe, it } from 'vitest'
import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { collectScreenState, mergeStates, stateEntry, formInventoryDocument } from 'usedesign'
import MyPanel from './src/MyPanel'                      // ПОД СЕБЯ: ваш компонент

const STATES = ['active', 'finished'] as const           // ПОД СЕБЯ: словарь состояний сущности

describe('usedesign form inventory', () => {
  it('renders the panels per entity state and dumps their anchors', () => {
    const forms = []
    const states = []
    for (const state of STATES) {
      const { unmount } = render(<MyPanel state={state} />)   // ПОД СЕБЯ: как задать состояние
      states.push(stateEntry(state, mergeStates([collectScreenState(document.body)])))
      unmount()
    }
    forms.push({ screen: 'MyPanel', states })

    const target = resolve(process.cwd(), 'usedesign', 'form-inventory.json')
    mkdirSync(resolve(process.cwd(), 'usedesign'), { recursive: true })
    writeFileSync(
      target,
      JSON.stringify(
        formInventoryDocument('runtime dump — components rendered per state by a vitest test', forms),
        null,
        2,
      ) + '\n',
      'utf8',
    )
  })
})

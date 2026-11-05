type Route = 'home' | 'annotate' | 'layout2'

export function NavLinks({ active }: { active: Route }) {
  return (
    <nav className="nav-links">
      <a href="#/" className={active === 'home' ? 'active' : undefined}>
        画布演示
      </a>
      <a href="#/annotate" className={active === 'annotate' ? 'active' : undefined}>
        手工标注
      </a>
      <a href="#/layout2" className={active === 'layout2' ? 'active' : undefined}>
        自适应布局
      </a>
    </nav>
  )
}

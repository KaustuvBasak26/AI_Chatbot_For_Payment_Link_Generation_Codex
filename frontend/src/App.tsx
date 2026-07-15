import { NavLink, Route, Routes } from 'react-router-dom'
import { ChatPage } from './pages/ChatPage'
import { DetailPage } from './pages/DetailPage'
import { HistoryPage } from './pages/HistoryPage'
import { MockPaymentPage } from './pages/MockPaymentPage'

function Shell() { return <><nav className="nav"><NavLink className="brand" to="/"><span>₹</span> PayLink</NavLink><div><NavLink to="/">Assistant</NavLink><NavLink to="/history">History</NavLink></div><span className="demo-pill">Demo mode</span></nav><Routes><Route path="/" element={<ChatPage/>}/><Route path="/history" element={<HistoryPage/>}/><Route path="/payments/:id" element={<DetailPage/>}/></Routes></> }
export default function App() { return <Routes><Route path="/pay/mock/:publicToken" element={<MockPaymentPage/>}/><Route path="*" element={<Shell/>}/></Routes> }


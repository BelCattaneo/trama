import { Route, Routes } from "react-router-dom";
import RedirectIfAuthed from "./components/RedirectIfAuthed";
import RequireAuth from "./components/RequireAuth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import DocumentsList from "./pages/DocumentsList";
import MapPage from "./pages/Map";
import MyOrders from "./pages/MyOrders";
import OrderDetail from "./pages/OrderDetail";
import Privacy from "./pages/Privacy";
import Review from "./pages/Review";
import Signup from "./pages/Signup";
import Upload from "./pages/Upload";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route
        path="/signup"
        element={
          <RedirectIfAuthed>
            <Signup />
          </RedirectIfAuthed>
        }
      />
      <Route
        path="/login"
        element={
          <RedirectIfAuthed>
            <Login />
          </RedirectIfAuthed>
        }
      />
      <Route
        path="/upload"
        element={
          <RequireAuth>
            <Upload />
          </RequireAuth>
        }
      />
      <Route
        path="/documents"
        element={
          <RequireAuth>
            <DocumentsList />
          </RequireAuth>
        }
      />
      <Route
        path="/my-orders"
        element={
          <RequireAuth>
            <MyOrders />
          </RequireAuth>
        }
      />
      <Route
        path="/review/:document_id"
        element={
          <RequireAuth>
            <Review />
          </RequireAuth>
        }
      />
      <Route
        path="/my-orders/:operation_id"
        element={
          <RequireAuth>
            <OrderDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/map"
        element={
          <RequireAuth>
            <MapPage />
          </RequireAuth>
        }
      />
    </Routes>
  );
}

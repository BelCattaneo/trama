import { Route, Routes } from "react-router-dom";
import RedirectIfAuthed from "./components/RedirectIfAuthed";
import RequireAuth from "./components/RequireAuth";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import DocumentsList from "./pages/DocumentsList";
import OperationsList from "./pages/OperationsList";
import Review from "./pages/Review";
import Signup from "./pages/Signup";
import Upload from "./pages/Upload";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
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
        path="/operations"
        element={
          <RequireAuth>
            <OperationsList />
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
    </Routes>
  );
}

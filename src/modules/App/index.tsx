import {lazy, Suspense} from 'react';
import {Routes, Route, Navigate} from 'react-router-dom';

const Welcome = lazy(() => import('@/modules/Welcome'));

export default function App() {
    return (
        <Suspense fallback={null}>
            <Routes>
                <Route path="welcome" element={<Welcome />} />
                <Route path="*" element={<Navigate replace to="/welcome" />} />
            </Routes>
        </Suspense>
    );
}

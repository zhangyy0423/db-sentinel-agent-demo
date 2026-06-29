import {StrictMode} from 'react';
import {render} from 'react-dom';
import {BrowserRouter} from 'react-router-dom';
import App from '@/modules/App';
import '@/styles';

const main = () => render(
    <StrictMode>
        <BrowserRouter>
            <App />
        </BrowserRouter>
    </StrictMode>,
    document.body.appendChild(document.createElement('div'))
);

main();

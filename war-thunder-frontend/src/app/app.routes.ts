import { Routes } from '@angular/router';
import { TankListComponent } from './components/tank-list/tank-list';

export const routes: Routes = [
    {path: "tanques", component: TankListComponent},
    { path: '**', redirectTo: 'tanques' }
];

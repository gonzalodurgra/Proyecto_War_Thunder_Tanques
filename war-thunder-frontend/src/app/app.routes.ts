import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './components/login/login';
import { RegisterComponent } from './components/register/register';
import { TankListComponent } from './components/tank-list/tank-list';

// ====================================================================
// DEFINIR LAS RUTAS DE LA APLICACIÓN
// ====================================================================
// EXPLICACIÓN:
// - path: La URL en el navegador
// - component: El componente que se mostrará
// - redirectTo: Redirige a otra ruta
// - pathMatch: 'full' significa que debe coincidir exactamente

export const routes: Routes = [
  // Ruta raíz - redirige al login
  {
    path: '',
    redirectTo: '/login',
    pathMatch: 'full'
  },
  
  // Ruta de login
  {
    path: 'login',
    component: LoginComponent
  },
  
  // Ruta de registro
  {
    path: 'register',
    component: RegisterComponent
  },
  
  // Ruta de tanques (principal)
  {
    path: 'tanques',
    component: TankListComponent
  },
  
  // Ruta 404 - cualquier ruta no definida redirige al login
  {
    path: '**',
    redirectTo: '/login'
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }

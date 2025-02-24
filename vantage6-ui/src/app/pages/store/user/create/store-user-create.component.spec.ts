import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StoreUserCreateComponent } from './store-user-create.component';

describe('StoreUserCreateComponent', () => {
  let component: StoreUserCreateComponent;
  let fixture: ComponentFixture<StoreUserCreateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StoreUserCreateComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(StoreUserCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

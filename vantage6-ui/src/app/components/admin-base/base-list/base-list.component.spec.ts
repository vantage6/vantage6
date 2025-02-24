import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BaseListComponent } from './base-list.component';

describe('BaseListComponent', () => {
  let component: BaseListComponent;
  let fixture: ComponentFixture<BaseListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BaseListComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(BaseListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

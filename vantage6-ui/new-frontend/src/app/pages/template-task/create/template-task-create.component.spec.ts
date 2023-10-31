import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TemplateTaskCreateComponent } from './template-task-create.component';

describe('TemplateTaskCreateComponent', () => {
  let component: TemplateTaskCreateComponent;
  let fixture: ComponentFixture<TemplateTaskCreateComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      declarations: [TemplateTaskCreateComponent]
    });
    fixture = TestBed.createComponent(TemplateTaskCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

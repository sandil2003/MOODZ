import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { NewHomeComponent } from './new-home';

describe('NewHomeComponent', () => {
  let component: NewHomeComponent;
  let fixture: ComponentFixture<NewHomeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewHomeComponent],
      providers: [provideRouter([])]
    })
    .compileComponents();

    fixture = TestBed.createComponent(NewHomeComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    fixture?.destroy();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
